#!/usr/bin/env bash
# Build ClankerMono.ttf, a small TTF for matplotlib charts, from ClankerMono-NF.ttf.
# matplotlib's bundled FreeType cannot read WOFF2, so charts need a TTF.
set -euo pipefail

cd "$(dirname "$0")"

source_font="ClankerMono-NF.ttf"
output_font="${1:-ClankerMono.ttf}"
# Latin-1, general punctuation, currency, arrows, and mathematical operators: the text a
# chart draws. Nerd Font icons, which carry their own licenses, are left out.
unicode_ranges="U+0020-007E,U+00A0-00FF,U+2000-206F,U+20A0-20CF,U+2190-21FF,U+2200-22FF"

uv run --no-config --with fonttools pyftsubset "$source_font" \
    --output-file="$output_font" \
    --unicodes="$unicode_ranges" \
    --layout-features='*' \
    --notdef-glyph \
    --notdef-outline \
    --recommended-glyphs

uv run --no-config --with fonttools --with brotli python rename_font.py \
    "$output_font" "$output_font" "Clanker Mono" \
    "tighter line spacing, a fix for its 18 ppem hinting of Latin i and two Cyrillic i glyphs, and a subset to Latin-1, punctuation, currency, arrows, and math"

stat -c '%s bytes %n' "$output_font"
