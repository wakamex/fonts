#!/usr/bin/env bash
# Build ClankerMono.ttf, a small TTF for matplotlib charts, from ClankerMono-Regular.ttf.
# matplotlib's bundled FreeType cannot read WOFF2, so charts need a TTF.
set -euo pipefail

cd "$(dirname "$0")"

source_font="ClankerMono-Regular.ttf"
output_font="${1:-ClankerMono.ttf}"
# Latin-1, general punctuation, currency, arrows, and mathematical operators: the text a
# chart draws.
unicode_ranges="U+0020-007E,U+00A0-00FF,U+2000-206F,U+20A0-20CF,U+2190-21FF,U+2200-22FF"

uv run --no-config --with fonttools pyftsubset "$source_font" \
    --output-file="$output_font" \
    --unicodes="$unicode_ranges" \
    --layout-features='*' \
    --name-IDs='*' \
    --notdef-glyph \
    --notdef-outline \
    --recommended-glyphs

uv run --no-config --with fonttools --with brotli python rename_font.py \
    "$output_font" "$output_font" "Clanker Mono" \
    "tighter line spacing and a subset to Latin-1, punctuation, currency, arrows, and math"

stat -c '%s bytes %n' "$output_font"
