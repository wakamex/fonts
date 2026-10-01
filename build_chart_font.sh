#!/usr/bin/env bash
# Build ClankerMono.ttf, a small TTF for matplotlib charts, from the customized
# D2CodingLigature.ttf. matplotlib's bundled FreeType cannot read WOFF2, so charts need a TTF.
# D2Coding's OFL 1.1 reserves the name "D2Coding", so this modified subset is renamed.
set -euo pipefail

cd "$(dirname "$0")"

source_font="D2CodingLigature.ttf"
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

uv run --no-config --with fonttools python - "$output_font" <<'PY'
import sys

from fontTools.ttLib import TTFont

path = sys.argv[1]
font = TTFont(path)
names = {
    1: "Clanker Mono",
    3: "Clanker Mono Regular",
    4: "Clanker Mono",
    6: "ClankerMono-Regular",
    16: "Clanker Mono",
}
table = font["name"]
for record in list(table.names):
    if record.nameID in names:
        table.setName(names[record.nameID], record.nameID, record.platformID,
                      record.platEncID, record.langID)
    elif record.nameID in {17, 21, 22}:
        table.removeNames(nameID=record.nameID)
for record in table.names:
    if "d2coding" in str(record).lower() and record.nameID not in {0, 13, 14}:
        raise SystemExit(f"reserved name left in name ID {record.nameID}: {record}")
font.save(path)
print(f"built {path} with {len(font.getGlyphOrder())} glyphs")
PY

stat -c '%s bytes %n' "$output_font"
