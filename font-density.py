#!/usr/bin/env python3
"""Measure information density of all fonts in programmingfonts.

Calculates character width, line height, and density score
(chars × lines per 1000×1000px) for each font at a given size.

Usage: python3 font-density.py [--size 16] [--spacing 1.4] [--sort density]
"""

import argparse
import json
import logging
import os
import sys

logging.getLogger("fontTools").setLevel(logging.ERROR)

from fontTools.ttLib import TTFont

PROGRAMMINGFONTS = "/code/programmingfonts"
FONTS_JSON = os.path.join(PROGRAMMINGFONTS, "fonts.json")
RESOURCES = os.path.join(PROGRAMMINGFONTS, "fonts/resources")


def load_font(path):
    """Load a font, decompressing WOFF2 if needed."""
    return TTFont(path)


def measure_font(font_path, font_size, line_spacing):
    """Return (char_width_px, line_height_px) at the given size and spacing."""
    font = load_font(font_path)

    upem = font["head"].unitsPerEm
    scale = font_size / upem

    # Character width: use advance width of 'x' or first available ASCII glyph
    hmtx = font["hmtx"]
    cmap = font.getBestCmap()
    advance = None
    for cp in [ord("x"), ord("M"), ord("0"), ord(" ")]:
        if cmap and cp in cmap:
            glyph_name = cmap[cp]
            advance = hmtx.metrics[glyph_name][0]
            break

    if advance is None:
        # Fallback: use xAvgCharWidth from OS/2
        advance = font["OS/2"].xAvgCharWidth

    char_width = advance * scale

    # Line height: hhea ascent + abs(descent), scaled, then multiplied by CSS line-height
    ascent = font["hhea"].ascent
    descent = abs(font["hhea"].descent)
    line_height = (ascent + descent) * scale * line_spacing

    font.close()
    return char_width, line_height


def find_font_file(alias):
    """Find the regular weight font file for a given alias."""
    resource_dir = os.path.join(RESOURCES, alias)
    if not os.path.isdir(resource_dir):
        return None

    # Prefer woff2, then ttf, skip bold/italic variants
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

    # Prefer the shortest name (usually the regular variant)
    candidates.sort(key=len)
    return os.path.join(resource_dir, candidates[0])


def main():
    parser = argparse.ArgumentParser(description="Measure font information density")
    parser.add_argument("--size", type=float, default=16, help="Font size in px (default: 16)")
    parser.add_argument("--spacing", type=float, default=1.0, help="Line spacing multiplier (default: 1.0)")
    parser.add_argument("--sort", choices=["density", "name", "width", "height"], default="density",
                        help="Sort by (default: density)")
    args = parser.parse_args()

    with open(FONTS_JSON) as f:
        fonts_data = json.load(f)

    results = []
    errors = []

    for alias, data in fonts_data.items():
        font_path = find_font_file(alias)
        if not font_path:
            errors.append(alias)
            continue

        try:
            char_w, line_h = measure_font(font_path, args.size, args.spacing)
            chars_per_line = 1000 / char_w if char_w > 0 else 0
            lines_per_screen = 1000 / line_h if line_h > 0 else 0
            density = int(chars_per_line * lines_per_screen)
            results.append({
                "alias": alias,
                "name": data["name"],
                "char_width": char_w,
                "line_height": line_h,
                "density": density,
            })
        except Exception as e:
            errors.append(f"{alias}: {e}")

    # Sort
    if args.sort == "density":
        results.sort(key=lambda r: r["density"], reverse=True)
    elif args.sort == "name":
        results.sort(key=lambda r: r["name"].lower())
    elif args.sort == "width":
        results.sort(key=lambda r: r["char_width"])
    elif args.sort == "height":
        results.sort(key=lambda r: r["line_height"])

    # Print table
    print(f"{'Font':<30s} {'Width':>6s} {'Height':>7s} {'Density':>8s}")
    print(f"{'':─<30s} {'':─>6s} {'':─>7s} {'':─>8s}")
    for r in results:
        print(f"{r['name']:<30s} {r['char_width']:>5.1f}px {r['line_height']:>6.1f}px {r['density']:>7,d}")

    if errors:
        print(f"\n({len(errors)} fonts skipped)", file=sys.stderr)


if __name__ == "__main__":
    main()
