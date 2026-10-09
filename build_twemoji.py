"""Build a Twemoji COLRv0 color emoji font from the Twemoji SVG graphics.

    uv run --with fonttools --with brotli --with nanoemoji python build_twemoji.py \
        --svg twemoji/assets/svg --emoji-test emoji-test.txt --out .

Writes ClankerTwemoji.ttf for desktop use and ClankerTwemoji.woff2 for the web. Every emoji
is a square one em wide, drawn from 125 units below the baseline to 875 above it. The SVG
files are named by code point sequence, as in jdecked/twemoji. Sequences that Twemoji draws
without U+FE0F are also reached with it, as the fully qualified sequences of emoji-test.txt
spell them, for example the red heart U+2764 U+FE0F.
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables._g_l_y_f import Glyph

FAMILY = "Clanker Twemoji"
VARIATION_SELECTOR = 0xFE0F
COPYRIGHT = "Twemoji graphics copyright Twitter, Inc. and other contributors"
LICENSE = "The graphics are licensed under the Creative Commons Attribution 4.0 International License."
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"


def qualified_sequences(emoji_test: Path) -> set[tuple[int, ...]]:
    sequences = set()
    for line in emoji_test.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or ";" not in line:
            continue
        codepoints, status = line.split("#")[0].split(";")
        if status.strip() == "fully-qualified":
            sequences.add(tuple(int(value, 16) for value in codepoints.split()))
    return sequences


def run_nanoemoji(svg: Path, scratch: Path) -> Path:
    sources = scratch / "svg"
    sources.mkdir()
    for path in sorted(svg.glob("*.svg")):
        stem = path.stem.replace("-", "_")
        shutil.copy(path, sources / f"emoji_u{stem}.svg")
    command = [
        shutil.which("nanoemoji"), "--color_format", "glyf_colr_0", "--upem", "1000",
        "--ascender", "875", "--descender", "-125", "--width", "1000", "--family", FAMILY,
        "--output_file", "font.ttf", "--build_dir", str(scratch / "build"),
        *map(str, sorted(sources.glob("*.svg"))),
    ]
    subprocess.run(command, check=True, cwd=scratch)
    return scratch / "build" / "font.ttf"


def ligature_lookup(font: TTFont) -> otTables.LigatureSubst:
    return next(
        subtable
        for record in font["GSUB"].table.LookupList.Lookup
        for subtable in record.SubTable
        if isinstance(subtable, otTables.LigatureSubst)
    )


def sequence_glyphs(font: TTFont) -> dict[tuple[int, ...], str]:
    """The glyph for each emoji: its cmap entry, or its ligature for a sequence."""
    cmap = font.getBestCmap()
    codepoint = {name: value for value, name in sorted(cmap.items(), reverse=True)}
    glyphs = {(value,): name for value, name in cmap.items()}
    for first, ligatures in ligature_lookup(font).ligatures.items():
        for ligature in ligatures:
            glyphs[tuple(codepoint[name] for name in (first, *ligature.Component))] = ligature.LigGlyph
    return glyphs


def add_variation_selector_sequences(font: TTFont, qualified: set[tuple[int, ...]]) -> int:
    """Add each fully qualified sequence that has U+FE0F and whose Twemoji image does not."""
    if VARIATION_SELECTOR not in font.getBestCmap():
        glyph_name = "uniFE0F"
        font.setGlyphOrder(font.getGlyphOrder() + [glyph_name])
        font["glyf"].glyphOrder = font.getGlyphOrder()
        font["glyf"].glyphs[glyph_name] = Glyph()
        font["hmtx"].metrics[glyph_name] = (0, 0)
        for table in font["cmap"].tables:
            if table.isUnicode():
                table.cmap[VARIATION_SELECTOR] = glyph_name
        font["maxp"].numGlyphs = len(font.getGlyphOrder())
    cmap = font.getBestCmap()
    glyphs = sequence_glyphs(font)

    additions = {}
    for sequence in qualified:
        stripped = tuple(value for value in sequence if value != VARIATION_SELECTOR)
        if sequence not in glyphs and stripped != sequence and stripped in glyphs:
            additions[sequence] = glyphs[stripped]

    lookup = ligature_lookup(font)
    for sequence, glyph in additions.items():
        first, *rest = (cmap[value] for value in sequence)
        ligature = otTables.Ligature()
        ligature.Component, ligature.LigGlyph = rest, glyph
        lookup.ligatures.setdefault(first, []).append(ligature)
    for ligatures in lookup.ligatures.values():
        ligatures.sort(key=lambda ligature: -len(ligature.Component))
    return len(additions)


def set_names(font: TTFont) -> None:
    names = {
        0: COPYRIGHT, 1: FAMILY, 2: "Regular", 3: f"{FAMILY} Regular", 4: FAMILY,
        6: FAMILY.replace(" ", "") + "-Regular", 13: LICENSE, 14: LICENSE_URL,
    }
    font["name"].names = []
    for name_id, text in names.items():
        font["name"].setName(text, name_id, 3, 1, 0x409)


def build(svg: Path, emoji_test: Path, out: Path) -> None:
    with tempfile.TemporaryDirectory() as scratch:
        font = TTFont(run_nanoemoji(svg, Path(scratch)))
        added = add_variation_selector_sequences(font, qualified_sequences(emoji_test))
        set_names(font)
        font.save(out / "ClankerTwemoji.ttf")
    print(f"{len(sequence_glyphs(font))} emoji codepoints and sequences, {added} with U+FE0F added")
    font = TTFont(out / "ClankerTwemoji.ttf")
    font.flavor = "woff2"
    font.save(out / "ClankerTwemoji.woff2")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--svg", type=Path, required=True, help="directory of Twemoji SVG files")
    parser.add_argument("--emoji-test", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("."))
    args = parser.parse_args()
    build(args.svg.resolve(), args.emoji_test, args.out)


if __name__ == "__main__":
    main()
