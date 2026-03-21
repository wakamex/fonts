#!/usr/bin/env python3
"""Measure ink coverage (glyph fill ratio) for programming fonts.

For each font, renders common code characters and measures what percentage
of the character cell is actually filled by ink. Higher = more visually dense.

Usage: python3 font-ink-coverage.py [--sort fill|name|combined] [--chars "abc..."]
"""

import argparse
import json
import logging
import os
import sys

logging.getLogger("fontTools").setLevel(logging.ERROR)

from fontTools.ttLib import TTFont
from fontTools.pens.statisticsPen import StatisticsPen

PROGRAMMINGFONTS = "/code/programmingfonts"
FONTS_JSON = os.path.join(PROGRAMMINGFONTS, "fonts.json")
RESOURCES = os.path.join(PROGRAMMINGFONTS, "fonts/resources")

# Characters that represent typical code
DEFAULT_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789{}[]()<>=+-*/|&!@#$%^~_;:.,\"\\'`"


def find_font_file(alias):
    resource_dir = os.path.join(RESOURCES, alias)
    if not os.path.isdir(resource_dir):
        return None
    candidates = []
    for f in os.listdir(resource_dir):
        if not f.endswith((".woff2", ".woff", ".ttf", ".otf")):
            continue
        lower = f.lower()
        if any(s in lower for s in ["bold", "italic", "oblique"]):
            continue
        candidates.append(f)
    if not candidates:
        return None
    candidates.sort(key=len)
    return os.path.join(resource_dir, candidates[0])


def measure_ink_coverage(font_path, chars, line_spacing=1.0):
    font = TTFont(font_path)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    if not cmap:
        font.close()
        return None, None

    ascent = font["hhea"].ascent
    descent = abs(font["hhea"].descent)
    # Include line spacing in cell height — this is what actually gets rendered
    cell_height = (ascent + descent) * line_spacing

    total_ink = 0
    total_cell = 0
    measured = 0

    for char in chars:
        cp = ord(char)
        if cp not in cmap:
            continue
        gname = cmap[cp]
        try:
            pen = StatisticsPen(gs)
            gs[gname].draw(pen)
            width = gs[gname].width
            if width <= 0:
                continue
            cell_area = width * cell_height
            ink_area = abs(pen.area)
            total_ink += ink_area
            total_cell += cell_area
            measured += 1
        except Exception:
            continue

    font.close()

    if measured == 0 or total_cell == 0:
        return None, None

    fill_ratio = total_ink / total_cell
    return fill_ratio, measured


def measure_cell_density(font_path, font_size=12, line_spacing=1.0):
    """Return density score (chars per 1000x1000px) like font-density.py."""
    font = TTFont(font_path)
    upem = font["head"].unitsPerEm
    scale = font_size / upem
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]

    advance = None
    for cp in [ord("x"), ord("M"), ord("0"), ord(" ")]:
        if cmap and cp in cmap:
            glyph_name = cmap[cp]
            advance = hmtx.metrics[glyph_name][0]
            break
    if advance is None:
        advance = font["OS/2"].xAvgCharWidth

    char_width = advance * scale
    ascent = font["hhea"].ascent
    descent = abs(font["hhea"].descent)
    line_height = (ascent + descent) * scale * line_spacing

    font.close()

    if char_width <= 0 or line_height <= 0:
        return 0
    return int((1000 / char_width) * (1000 / line_height))


def main():
    parser = argparse.ArgumentParser(description="Measure font ink coverage")
    parser.add_argument(
        "--sort",
        choices=["fill", "name", "combined", "density"],
        default="combined",
        help="Sort by (default: combined = fill × density)",
    )
    parser.add_argument(
        "--chars", default=DEFAULT_CHARS, help="Characters to measure"
    )
    parser.add_argument(
        "--textsample", help="Read characters from a file instead of --chars"
    )
    args = parser.parse_args()

    if args.textsample:
        text = open(args.textsample).read()
        args.chars = "".join(sorted(set(c for c in text if c.isprintable() and 32 < ord(c) < 0x10000)))

    with open(FONTS_JSON) as f:
        fonts_data = json.load(f)

    results = []
    errors = 0

    for alias, data in fonts_data.items():
        font_path = find_font_file(alias)
        if not font_path:
            errors += 1
            continue
        try:
            fill, measured = measure_ink_coverage(font_path, args.chars)
            density = measure_cell_density(font_path)
            if fill is None:
                errors += 1
                continue
            combined = fill * density
            results.append({
                "alias": alias,
                "name": data["name"],
                "fill": fill,
                "measured": measured,
                "density": density,
                "combined": combined,
            })
        except Exception:
            errors += 1

    sort_key = {
        "fill": lambda r: r["fill"],
        "name": lambda r: r["name"].lower(),
        "density": lambda r: r["density"],
        "combined": lambda r: r["combined"],
    }
    reverse = args.sort != "name"
    results.sort(key=sort_key[args.sort], reverse=reverse)

    print(f"{'Font':<30s} {'Fill':>5s} {'Density':>8s} {'Combined':>9s}")
    print(f"{'':─<30s} {'':─>5s} {'':─>8s} {'':─>9s}")
    for r in results:
        print(
            f"{r['name']:<30s} {r['fill']:>4.0%} {r['density']:>7,d} {r['combined']:>8,.0f}"
        )

    if errors:
        print(f"\n({errors} fonts skipped)", file=sys.stderr)


if __name__ == "__main__":
    main()
