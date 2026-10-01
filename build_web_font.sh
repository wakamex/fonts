#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

source_font="ClankerMono-NF.ttf"
output_font="ClankerMono-web.woff2"
unicode_ranges="U+0000-024F,U+0370-03FF,U+1E00-1EFF,U+2000-206F,U+20A0-22FF,U+2500-27BF"

uv run --with fonttools --with brotli pyftsubset "$source_font" \
    --output-file="$output_font" \
    --flavor=woff2 \
    --unicodes="$unicode_ranges" \
    --layout-features='*' \
    --name-IDs='*' \
    --name-legacy \
    --name-languages='*' \
    --glyph-names \
    --symbol-cmap \
    --legacy-cmap \
    --notdef-glyph \
    --notdef-outline \
    --recommended-glyphs

uv run --no-config --with fonttools --with brotli python rename_font.py \
    "$output_font" "$output_font" "Clanker Mono" \
    "Nerd Fonts 2.3.0-RC patching, tighter line spacing, a fix for its 18 ppem hinting of Latin i and two Cyrillic i glyphs, and a subset to Latin, Greek, punctuation, currency, arrows, math, and box drawing"

uv run --with fonttools --with brotli python - "$source_font" "$output_font" <<'PY'
import sys

from fontTools.ttLib import TTFont


def metrics(path):
    font = TTFont(path)
    return (
        font["head"].unitsPerEm,
        font["hhea"].ascent,
        font["hhea"].descent,
        font["hhea"].lineGap,
        font["OS/2"].sTypoAscender,
        font["OS/2"].sTypoDescender,
        font["OS/2"].sTypoLineGap,
    )


source, output = sys.argv[1:]
if metrics(source) != metrics(output):
    raise SystemExit("vertical metrics changed during subsetting")

font = TTFont(output)
codepoints = {
    codepoint
    for table in font["cmap"].tables
    if table.isUnicode()
    for codepoint in table.cmap
}
required = set(range(0x20, 0x7F))
missing = required - codepoints
if missing:
    raise SystemExit(f"web font is missing printable ASCII: {sorted(missing)}")

print(f"built {output} with {len(font.getGlyphOrder())} glyphs")
PY

stat -c '%s bytes %n' "$output_font"
