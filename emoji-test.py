#!/usr/bin/env python3
"""Test emoji support in a font file.

Usage: python3 emoji-test.py [font_path]

Supports .ttf, .otf, and .woff2 files. WOFF2 files are decompressed
to raw OpenType in memory before testing (works around a HarfBuzz
WOFF2 shaping limitation).

Without arguments, downloads ClankerMono-NF.ttf from mihaicosma.com.
"""

import codecs
import io
import os
import subprocess
import sys
import urllib.request
from typing import Tuple

try:
    import uharfbuzz as hb
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "uharfbuzz"])
    import uharfbuzz as hb

EMOJI_TEST_URL = "https://unicode.org/Public/emoji/15.0/emoji-test.txt"
DEFAULT_FONT_URL = "https://mihaicosma.com/ClankerMono-NF.ttf"
EMOJI_TEST_FILE = os.path.join(os.path.dirname(__file__), "emoji-test.txt")


def load_font_data(file_path: str) -> bytes:
    """Load font data, decompressing WOFF2 to raw TTF if needed."""
    if file_path.endswith(".woff2"):
        from fontTools.ttLib import TTFont

        font = TTFont(file_path)
        buf = io.BytesIO()
        font.flavor = None
        font.save(buf)
        buf.seek(0)
        return buf.read()
    with open(file_path, "rb") as f:
        return f.read()


def is_emoji_supported(font, emoji: str) -> Tuple[bool, Tuple]:
    buf = hb.Buffer.create()
    buf.add_str(emoji)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": 1, "liga": 1})
    infos = buf.glyph_infos
    return len(infos) == 1 and infos[0].cluster == 0, infos


def codepoint_str(s):
    return " ".join(f"U+{ord(c):04X}" for c in s)


def main():
    # Resolve font path
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "ClankerMono-NF.ttf"

    if not os.path.exists(file_path):
        if len(sys.argv) > 1:
            print(f"Error: {file_path} not found", file=sys.stderr)
            sys.exit(1)
        print("Downloading default font...", end="", flush=True)
        urllib.request.urlretrieve(DEFAULT_FONT_URL, file_path)
        print(" done")

    # Load font
    print(f"Font: {file_path}")
    fontdata = load_font_data(file_path)
    font = hb.Font(hb.Face(hb.Blob(fontdata)))

    # Quick single-emoji sanity check
    test = "🤗"
    ok, _ = is_emoji_supported(font, test)
    print(f"Sanity check: {test} supported={ok}\n")

    # Download emoji-test.txt if needed
    if not os.path.exists(EMOJI_TEST_FILE):
        print("Downloading emoji-test.txt...", end="", flush=True)
        urllib.request.urlretrieve(EMOJI_TEST_URL, EMOJI_TEST_FILE)
        print(" done")

    # Run full test
    supported_count = 0
    unsupported_count = 0

    with open(EMOJI_TEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(";")
            if len(parts) < 2:
                continue

            code_points = parts[0].strip()
            rest = parts[1].strip()
            status, _, comment = rest.partition("#")
            status = status.strip()
            comment = comment.strip()

            # First token of comment is the emoji character(s)
            tokens = comment.split(" ", 1)
            emoji = tokens[0]
            name = tokens[1] if len(tokens) > 1 else ""

            ok, infos = is_emoji_supported(font, emoji)
            if ok:
                supported_count += 1
                print(
                    f"  {emoji}  {status:<20s} {codepoint_str(emoji):<30s} {name}"
                )
            else:
                unsupported_count += 1

    total = supported_count + unsupported_count
    pct = supported_count / total * 100 if total else 0
    print(f"\nsupported={supported_count:,}  unsupported={unsupported_count:,}  total={total:,}  ({pct:.1f}%)")


if __name__ == "__main__":
    main()
