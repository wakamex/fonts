#!/usr/bin/env python3
"""Merge Twemoji COLRv0 color emoji into a TrueType font.

Usage: python3 merge_twemoji.py <base_font.ttf> <twemoji.ttf> <output.ttf>

Copies all Twemoji glyphs, COLR/CPAL color tables, and GSUB ligature
sequences (for ZWJ, skin tones, keycaps, flags) into the base font.
Overlapping codepoints keep the base font's text-presentation glyph;
the color emoji version is only reached via GSUB when a variation
selector (U+FE0F) or other combining sequence is present.
"""

import sys
import copy
from collections import OrderedDict

from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable


def merge_fonts(base_path, emoji_path, output_path):
    print(f"Loading {base_path}...")
    base = TTFont(base_path)
    print(f"Loading {emoji_path}...")
    emoji = TTFont(emoji_path)

    # ── Step 0: Scale emoji upem to match base ─────────────────────────
    base_upem = base["head"].unitsPerEm
    emoji_upem = emoji["head"].unitsPerEm
    if base_upem != emoji_upem:
        print(f"Scaling emoji font {emoji_upem} → {base_upem} upem...")
        scale_upem(emoji, base_upem)

    # ── Step 1: Build overlap mapping ──────────────────────────────────
    base_cmap = base.getBestCmap()
    emoji_cmap = emoji.getBestCmap()

    # emoji_glyph_name → base_glyph_name  (for codepoints that exist in both)
    overlap_remap = {}
    for cp in set(emoji_cmap) & set(base_cmap):
        overlap_remap[emoji_cmap[cp]] = base_cmap[cp]

    print(f"Codepoint overlap: {len(overlap_remap)} glyphs")

    # ── Step 2: Copy all emoji glyphs ──────────────────────────────────
    emoji_order = emoji.getGlyphOrder()
    base_order = list(base.getGlyphOrder())
    existing = set(base_order)

    SKIP = {".notdef", ".null", "nonmarkingreturn", "NULL"}
    name_map = {}  # emoji_name → name in merged font
    new_glyphs = []

    for gname in emoji_order:
        if gname in SKIP:
            continue
        target = gname
        if gname in existing:
            target = f"tw.{gname}"
        name_map[gname] = target

        # Copy glyf outline
        if gname in emoji["glyf"]:
            base["glyf"][target] = copy.deepcopy(emoji["glyf"][gname])

        # Copy horizontal metrics
        base["hmtx"][target] = emoji["hmtx"][gname]

        new_glyphs.append(target)
        existing.add(target)

    conflicts = {k: v for k, v in name_map.items() if k != v}
    if conflicts:
        print(f"  Renamed {len(conflicts)} conflicting glyphs (tw.* prefix)")

    # Fix composite glyph references (now that name_map is complete)
    for gname in emoji_order:
        if gname in SKIP:
            continue
        target = name_map[gname]
        g = base["glyf"].get(target)
        if g and g.isComposite():
            for comp in g.components:
                comp.glyphName = name_map.get(comp.glyphName, comp.glyphName)

    # Update glyph order
    base.setGlyphOrder(base_order + new_glyphs)
    print(f"Copied {len(new_glyphs)} glyphs")

    # ── Step 3: Add cmap entries for emoji-only codepoints ─────────────
    # Ensure a format-12 subtable exists (needed for codepoints > U+FFFF)
    has_fmt12 = any(
        t.format == 12 for t in base["cmap"].tables if hasattr(t, "cmap") and t.cmap
    )
    if not has_fmt12:
        fmt12 = CmapSubtable.newSubtable(12)
        fmt12.platEncID = 3
        fmt12.platformID = 3
        fmt12.format = 12
        fmt12.reserved = 0
        fmt12.length = 0
        fmt12.language = 0
        fmt12.groups = []
        fmt12.cmap = {}
        # Seed with existing BMP entries
        fmt4 = next(
            (
                t
                for t in base["cmap"].tables
                if t.format == 4 and t.platformID == 3
            ),
            None,
        )
        if fmt4:
            fmt12.cmap.update(fmt4.cmap)
        base["cmap"].tables.append(fmt12)
        print("  Created format-12 cmap subtable for supplementary planes")

    # Also add format-12 for platformID=0 (Unicode) if not present
    has_uni_fmt12 = any(
        t.format == 12 and t.platformID == 0
        for t in base["cmap"].tables
        if hasattr(t, "cmap") and t.cmap
    )
    if not has_uni_fmt12:
        fmt12_uni = CmapSubtable.newSubtable(12)
        fmt12_uni.platEncID = 4
        fmt12_uni.platformID = 0
        fmt12_uni.format = 12
        fmt12_uni.reserved = 0
        fmt12_uni.length = 0
        fmt12_uni.language = 0
        fmt12_uni.groups = []
        fmt12_uni.cmap = {}
        fmt4_uni = next(
            (
                t
                for t in base["cmap"].tables
                if t.format == 4 and t.platformID == 0
            ),
            None,
        )
        if fmt4_uni:
            fmt12_uni.cmap.update(fmt4_uni.cmap)
        base["cmap"].tables.append(fmt12_uni)

    added_cmap = 0
    for cp, gname in emoji_cmap.items():
        if cp not in base_cmap:
            target = name_map.get(gname, gname)
            for table in base["cmap"].tables:
                if not hasattr(table, "cmap") or table.cmap is None:
                    continue
                if table.format == 4 and cp > 0xFFFF:
                    continue  # format 4 can't handle supplementary planes
                if table.format == 6:
                    continue  # leave Mac subtable alone
                table.cmap[cp] = target
            added_cmap += 1
    print(f"Added {added_cmap} cmap entries")

    # ── Step 4: Copy COLR table ────────────────────────────────────────
    emoji_colr = emoji["COLR"]
    new_layers = OrderedDict()
    for base_glyph, layers in emoji_colr.ColorLayers.items():
        new_base = name_map.get(base_glyph, base_glyph)
        new_layer_list = []
        for layer in layers:
            new_layer = copy.deepcopy(layer)
            new_layer.name = name_map.get(layer.name, layer.name)
            new_layer_list.append(new_layer)
        new_layers[new_base] = new_layer_list

    base_colr = copy.deepcopy(emoji_colr)
    base_colr.ColorLayers = new_layers
    base["COLR"] = base_colr
    print(f"Copied COLR: {len(new_layers)} base glyphs")

    # ── Step 5: Copy CPAL table ────────────────────────────────────────
    base["CPAL"] = copy.deepcopy(emoji["CPAL"])
    print(f"Copied CPAL: {emoji['CPAL'].numPaletteEntries} palette entries")

    # ── Step 6: Merge GSUB ─────────────────────────────────────────────
    # Build the full glyph remap for GSUB:
    #  - overlapping codepoints → base font's glyph name (cmap produces those)
    #  - everything else → name_map (handles tw.* renames)
    gsub_remap = {}
    for emoji_name, base_name in overlap_remap.items():
        gsub_remap[emoji_name] = base_name
    for emoji_name, merged_name in name_map.items():
        if emoji_name not in gsub_remap:
            gsub_remap[emoji_name] = merged_name

    emoji_gsub = emoji["GSUB"].table
    base_gsub = base["GSUB"].table

    base_lookup_count = len(base_gsub.LookupList.Lookup)
    new_lookup_indices = []

    for i, lookup in enumerate(emoji_gsub.LookupList.Lookup):
        new_lookup = copy.deepcopy(lookup)

        for subtable in new_lookup.SubTable:
            if hasattr(subtable, "ligatures"):
                # LigatureSubst (type 4)
                remapped = {}
                for first_glyph, lig_list in subtable.ligatures.items():
                    remapped_first = gsub_remap.get(first_glyph, first_glyph)
                    new_lig_list = []
                    for lig in lig_list:
                        lig.Component = [
                            gsub_remap.get(c, c) for c in lig.Component
                        ]
                        lig.LigGlyph = gsub_remap.get(lig.LigGlyph, lig.LigGlyph)
                        new_lig_list.append(lig)
                    # Merge if same first glyph already exists
                    if remapped_first in remapped:
                        remapped[remapped_first].extend(new_lig_list)
                    else:
                        remapped[remapped_first] = new_lig_list
                subtable.ligatures = remapped

            elif hasattr(subtable, "mapping"):
                # SingleSubst (type 1)
                remapped = {}
                for inp, out in subtable.mapping.items():
                    remapped[gsub_remap.get(inp, inp)] = gsub_remap.get(out, out)
                subtable.mapping = remapped

        base_gsub.LookupList.Lookup.append(new_lookup)
        new_lookup_indices.append(base_lookup_count + i)

    # Add ccmp feature record
    feat_record = otTables.FeatureRecord()
    feat_record.FeatureTag = "ccmp"
    feat_record.Feature = otTables.Feature()
    feat_record.Feature.FeatureParams = None
    feat_record.Feature.LookupListIndex = new_lookup_indices
    feat_record.Feature.LookupCount = len(new_lookup_indices)

    ccmp_index = len(base_gsub.FeatureList.FeatureRecord)
    base_gsub.FeatureList.FeatureRecord.append(feat_record)
    base_gsub.FeatureList.FeatureCount = len(base_gsub.FeatureList.FeatureRecord)

    # Register ccmp in all scripts' language systems
    for script_record in base_gsub.ScriptList.ScriptRecord:
        if script_record.Script.DefaultLangSys:
            dls = script_record.Script.DefaultLangSys
            dls.FeatureIndex.append(ccmp_index)
            dls.FeatureCount = len(dls.FeatureIndex)
        for lang_sys_record in script_record.Script.LangSysRecord:
            ls = lang_sys_record.LangSys
            ls.FeatureIndex.append(ccmp_index)
            ls.FeatureCount = len(ls.FeatureIndex)

    lig_count = sum(
        sum(len(v) for v in st.ligatures.values())
        for lk in emoji_gsub.LookupList.Lookup
        for st in lk.SubTable
        if hasattr(st, "ligatures")
    )
    print(f"Merged GSUB: {len(new_lookup_indices)} lookups, ~{lig_count} ligatures")

    # ── Step 7: Update GDEF ────────────────────────────────────────────
    final_glyphs = set(base.getGlyphOrder())
    if "GDEF" in base and "GDEF" in emoji:
        base_gdef = base["GDEF"].table
        emoji_gdef = emoji["GDEF"].table
        if (
            hasattr(base_gdef, "GlyphClassDef")
            and base_gdef.GlyphClassDef
            and hasattr(emoji_gdef, "GlyphClassDef")
            and emoji_gdef.GlyphClassDef
        ):
            for gname, cls in emoji_gdef.GlyphClassDef.classDefs.items():
                target = name_map.get(gname, gname)
                if target in final_glyphs and target not in base_gdef.GlyphClassDef.classDefs:
                    base_gdef.GlyphClassDef.classDefs[target] = cls
            # Remove any stale entries referencing glyphs not in the font
            base_gdef.GlyphClassDef.classDefs = {
                k: v
                for k, v in base_gdef.GlyphClassDef.classDefs.items()
                if k in final_glyphs
            }
            print(
                f"Updated GDEF: {len(base_gdef.GlyphClassDef.classDefs)} class defs"
            )

    # ── Step 8: Update maxp ────────────────────────────────────────────
    base["maxp"].numGlyphs = len(base.getGlyphOrder())

    # ── Step 9: Save ───────────────────────────────────────────────────
    print(f"\nSaving {output_path}...")
    base.save(output_path)
    print("Done!")

    # Quick verification
    result = TTFont(output_path)
    rcmap = result.getBestCmap()
    print(f"\nVerification:")
    print(f"  Total glyphs: {len(result.getGlyphOrder()):,}")
    print(f"  Cmap entries: {len(rcmap):,}")
    print(f"  Has COLR: {'COLR' in result}")
    print(f"  Has CPAL: {'CPAL' in result}")
    emoji_cp = sum(1 for cp in rcmap if cp >= 0x1F000)
    print(f"  Emoji codepoints (U+1F000+): {emoji_cp:,}")
    result.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <base.ttf> <twemoji.ttf> <output.ttf>")
        sys.exit(1)
    merge_fonts(sys.argv[1], sys.argv[2], sys.argv[3])
