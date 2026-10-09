"""Build the Clanker Mono fonts from NAVER's D2Coding ligature releases.

    uv run --with fonttools --with brotli python build_fonts.py \
        --regular D2Codingligature-Regular.ttf --bold D2Codingligature-Bold.ttf \
        --icons ClankerMono-NF.ttf --twemoji twemoji-colr.ttf

Every build has tighter line spacing than D2Coding: no line gap in the hhea table, and
OS/2 typographic metrics that match the Windows ones. The builds are:

    ClankerMono-Regular.ttf, ClankerMono-Bold.ttf   D2Coding with the tighter spacing
    ClankerMono-NF.ttf                              Regular plus the Nerd Fonts icons
    ClankerMono-Emoji.ttf, ClankerMono-Emoji.woff2  NF without Hangul, plus Twemoji

The Nerd Fonts icons are copied from the --icons font, which is the previous
ClankerMono-NF.ttf: its private use area and power symbol glyphs are the Nerd Fonts 2.3.0-RC
icons, and its other glyphs are not used. Copying them keeps the icon set unchanged across
D2Coding releases.
"""

import argparse
import tempfile
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

from merge_twemoji import merge_fonts
from rename_font import rename

# The icons outside the private use area, which starts at U+E000.
POWER_SYMBOLS = {0x23FB, 0x23FC, 0x23FD, 0x23FE, 0x2B58}
HANGUL_SYLLABLES = range(0xAC00, 0xD7A4)
TIGHT_TYPO_METRICS = {"sTypoAscender": 930, "sTypoDescender": -230, "sTypoLineGap": 0}


def tighten_spacing(font: TTFont) -> None:
    font["hhea"].lineGap = 0
    for name, value in TIGHT_TYPO_METRICS.items():
        setattr(font["OS/2"], name, value)


def add_icons(font: TTFont, icons: TTFont) -> int:
    """Copy the icon glyphs of `icons` that `font` does not map; return how many."""
    mapped = font.getBestCmap()
    icon_cmap = icons.getBestCmap()
    codepoints = {
        codepoint
        for codepoint in icon_cmap
        if (codepoint >= 0xE000 or codepoint in POWER_SYMBOLS) and codepoint not in mapped
    }
    names = sorted({icon_cmap[codepoint] for codepoint in codepoints}, key=icons.getGlyphID)
    if set(names) & set(font.getGlyphOrder()):
        raise SystemExit("an icon glyph name is already used")

    order = font.getGlyphOrder() + names
    font.setGlyphOrder(order)
    font["glyf"].glyphOrder = order
    classes = font["GDEF"].table.GlyphClassDef.classDefs
    for name in names:
        glyph = icons["glyf"][name]
        if glyph.isComposite():
            raise SystemExit(f"icon glyph {name} is a composite")
        advance, side_bearing = icons["hmtx"].metrics[name]
        # FreeType shifts a glyph by its left side bearing minus xMin. Saving recomputes xMin
        # from the points, so keep that shift as it was.
        shift = side_bearing - glyph.xMin if glyph.numberOfContours else 0
        font["glyf"].glyphs[name] = glyph
        glyph.recalcBounds(font["glyf"])
        font["hmtx"].metrics[name] = (advance, glyph.xMin + shift if glyph.numberOfContours else side_bearing)
        classes[name] = 1
    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap.update({codepoint: icon_cmap[codepoint] for codepoint in codepoints})
    font["maxp"].numGlyphs = len(order)
    font["OS/2"].recalcAvgCharWidth(font)
    return len(codepoints)


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
    nf_changes = f"Nerd Fonts 2.3.0-RC icons and {base_changes}"
    emoji_changes = f"Nerd Fonts 2.3.0-RC icons, Twemoji color emoji, Hangul removed, and {base_changes}"

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
    parser.add_argument("--icons", type=Path, required=True, help="previous ClankerMono-NF.ttf")
    parser.add_argument("--twemoji", type=Path, required=True, help="Twemoji COLRv0 font")
    parser.add_argument("--out", type=Path, default=Path("."))
    args = parser.parse_args()
    build(args.regular, args.bold, args.icons, args.twemoji, args.out)


if __name__ == "__main__":
    main()
