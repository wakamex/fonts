#!/usr/bin/env bash
# Patch a D2Coding ligature Regular font with the Nerd Fonts icons, for build_fonts.py --icons.
#
#   ./patch_nerd_fonts.sh FONT_PATCHER_DIR D2Codingligature-Regular.ttf OUTPUT_DIR
#
# FONT_PATCHER_DIR is the unpacked FontPatcher.zip of a Nerd Fonts release (this repository
# uses v3.5.1) and needs FontForge with its Python module. The patched font is written to
# OUTPUT_DIR with the patcher's own file name. Only its icon glyphs are used.
set -euo pipefail

patcher_dir="$1"
font="$2"
output_dir="$3"

fontforge -quiet -script "$patcher_dir/font-patcher" "$font" \
    --complete --no-progressbars --outputdir "$output_dir"
