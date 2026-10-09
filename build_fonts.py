"""Build the Clanker Mono fonts from NAVER's D2Coding ligature releases.

    uv run --with fonttools --with brotli python build_fonts.py \
        --regular D2Codingligature-Regular.ttf --bold D2Codingligature-Bold.ttf \
        --icons ClankerMono-NF.ttf --twemoji twemoji-colr.ttf

Every build has tighter line spacing than D2Coding: no line gap in the hhea table, and
OS/2 typographic metrics that match the Windows ones. The builds are:

    ClankerMono-Regular.ttf, ClankerMono-Bold.ttf   D2Coding with the tighter spacing
    ClankerMono-NF.ttf                              Regular plus the Nerd Fonts icons
    ClankerMono-Emoji.ttf, ClankerMono-Emoji.woff2  NF without Hangul, plus Twemoji

The Nerd Fonts icons are the glyphs of the --icons font, a D2Coding Regular patched by
patch_nerd_fonts.sh, for codepoints that D2Coding does not map. D2Coding's own glyphs are kept
where the patcher overwrote them.
"""

import argparse
import tempfile
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

from merge_twemoji import merge_fonts
from rename_font import rename

HANGUL_SYLLABLES = range(0xAC00, 0xD7A4)
TIGHT_TYPO_METRICS = {"sTypoAscender": 930, "sTypoDescender": -230, "sTypoLineGap": 0}


def tighten_spacing(font: TTFont) -> None:
    font["hhea"].lineGap = 0
    for name, value in TIGHT_TYPO_METRICS.items():
        setattr(font["OS/2"], name, value)


def add_icons(font: TTFont, icons: TTFont) -> int:
    """Copy the glyphs of `icons` for codepoints that `font` does not map; return how many."""
    mapped = font.getBestCmap()
    icon_cmap = icons.getBestCmap()
    codepoints = {codepoint for codepoint in icon_cmap if codepoint not in mapped}
    names = sorted({icon_cmap[codepoint] for codepoint in codepoints}, key=icons.getGlyphID)
    taken = set(font.getGlyphOrder())
    rename = {}
    for name in names:
        unique = name
        while unique in taken:
            unique = f"nf.{unique}"
        taken.add(unique)
        rename[name] = unique

    order = font.getGlyphOrder() + [rename[name] for name in names]
    font.setGlyphOrder(order)
    font["glyf"].glyphOrder = order
    classes = font["GDEF"].table.GlyphClassDef.classDefs
    for name in names:
        glyph = icons["glyf"][name]
        if glyph.isComposite():
            raise SystemExit(f"icon glyph {name} is a composite")
        glyph.removeHinting()
        advance, side_bearing = icons["hmtx"].metrics[name]
        # FreeType shifts a glyph by its left side bearing minus xMin. Saving recomputes xMin
        # from the points, so keep that shift as it was.
        shift = side_bearing - glyph.xMin if glyph.numberOfContours else 0
        new_name = rename[name]
        font["glyf"].glyphs[new_name] = glyph
        glyph.recalcBounds(font["glyf"])
        font["hmtx"].metrics[new_name] = (advance, glyph.xMin + shift if glyph.numberOfContours else side_bearing)
        classes[new_name] = 1

    add_codepoints(font, {codepoint: rename[icon_cmap[codepoint]] for codepoint in codepoints})
    font["maxp"].numGlyphs = len(order)
    font["OS/2"].recalcAvgCharWidth(font)
    font["OS/2"].recalcUnicodeRanges(font)
    return len(codepoints)


def add_codepoints(font: TTFont, entries: dict[int, str]) -> None:
    """Map `entries` in every Unicode cmap; supplementary codepoints get format 12 tables."""
    tables = font["cmap"].tables
    if any(codepoint > 0xFFFF for codepoint in entries) and not any(t.format == 12 for t in tables):
        for platform, encoding in ((0, 4), (3, 10)):
            table = CmapSubtable.newSubtable(12)
            table.platformID, table.platEncID, table.language = platform, encoding, 0
            table.cmap = dict(font.getBestCmap())
            tables.append(table)
    for table in tables:
        if not table.isUnicode():
            continue
        limit = 0xFFFF if table.format == 4 else 0x10FFFF
        table.cmap.update({c: n for c, n in entries.items() if c <= limit})


def remove_hangul(source: Path, output: Path) -> None:
    font = TTFont(source)
    keep = set(font.getBestCmap()) - set(HANGUL_SYLLABLES)
    options = subset.Options(
        layout_features=["*"],
        name_IDs=["*"],
        name_legacy=True,
        name_languages=["*"],
        notdef_outline=True,
        glyph_names=True,
        legacy_cmap=True,
        symbol_cmap=True,
        recommended_glyphs=True,
    )
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=keep)
    subsetter.subset(font)
    font.save(output)


def build(regular: Path, bold: Path, icons: Path, twemoji: Path, out: Path) -> None:
    base_changes = "tighter line spacing"
    nf_changes = f"Nerd Fonts 3.5.1 icons and {base_changes}"
    emoji_changes = f"Nerd Fonts 3.5.1 icons, Twemoji color emoji, Hangul removed, and {base_changes}"

    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        for source, style in ((regular, "Regular"), (bold, "Bold")):
            font = TTFont(source)
            tighten_spacing(font)
            font.save(scratch / f"tight-{style}.ttf")
            rename(scratch / f"tight-{style}.ttf", out / f"ClankerMono-{style}.ttf",
                   "Clanker Mono", base_changes)

        font = TTFont(scratch / "tight-Regular.ttf")
        print(f"{add_icons(font, TTFont(icons))} icons added")
        font.save(scratch / "nf.ttf")
        rename(scratch / "nf.ttf", out / "ClankerMono-NF.ttf", "Clanker Mono NF", nf_changes)

        remove_hangul(scratch / "nf.ttf", scratch / "nf-no-hangul.ttf")
        merge_fonts(str(scratch / "nf-no-hangul.ttf"), str(twemoji), str(scratch / "emoji.ttf"))
        rename(scratch / "emoji.ttf", out / "ClankerMono-Emoji.ttf", "Clanker Mono Emoji",
               emoji_changes)

    emoji = TTFont(out / "ClankerMono-Emoji.ttf")
    emoji.flavor = "woff2"
    emoji.save(out / "ClankerMono-Emoji.woff2")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--regular", type=Path, required=True, help="D2Coding ligature Regular")
    parser.add_argument("--bold", type=Path, required=True, help="D2Coding ligature Bold")
    parser.add_argument("--icons", type=Path, required=True, help="D2Coding Regular patched with Nerd Fonts")
    parser.add_argument("--twemoji", type=Path, required=True, help="Twemoji COLRv0 font")
    parser.add_argument("--out", type=Path, default=Path("."))
    args = parser.parse_args()
    build(args.regular, args.bold, args.icons, args.twemoji, args.out)


if __name__ == "__main__":
    main()
