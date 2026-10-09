"""Rename a modified D2Coding build and keep NAVER's credits.

D2Coding's OFL 1.1 reserves the name "D2Coding", so modified builds carry another family
name. The copyright, trademark, manufacturer, designer, URL and license records are taken
from the source font, so a build made from an upstream release carries that release's
credits. The family, style, unique ID, full name, version and description are written
fresh. Every other name record, including Korean and Mac ones that repeated the old name,
is dropped, except the feature names (IDs 256 and up) that the font's OpenType features
refer to.

    uv run --with fonttools --with brotli python rename_font.py SOURCE OUTPUT FAMILY CHANGES
"""

import argparse
import re
import time
from pathlib import Path

from fontTools.misc.timeTools import timestampFromString
from fontTools.ttLib import TTFont

CREDITS = (0, 7, 8, 9, 11, 12, 13, 14)
# Copyright, trademark, and license notices may name the original font.
NOTICES = {0, 7, 10, 13, 14}
BOLD = 1 << 5


def rename(source: Path, output: Path, family: str, changes: str) -> None:
    font = TTFont(source)
    table = font["name"]
    kept = {
        record.nameID: record.toUnicode()
        for record in table.names
        if (record.platformID, record.langID) == (3, 0x409)
    }
    version = kept[5].removesuffix("; modified")
    upstream_version = re.match(r"Version (\S+?);", version)[1]
    style = "Bold" if font["OS/2"].fsSelection & BOLD else "Regular"
    full_name = family if style == "Regular" else f"{family} {style}"
    feature_names = [
        record for record in table.names if record.nameID >= 256 and record.platformID == 3
    ]

    names = {
        **{name_id: kept[name_id] for name_id in CREDITS},
        1: family,
        2: style,
        3: f"{family} {style}",
        4: full_name,
        5: f"{version}; modified",
        6: f"{family.replace(' ', '')}-{style}",
        10: f"Modified from the D2Coding {upstream_version} ligature font by NAVER Corporation: "
            f"{changes}.",
    }
    table.names = feature_names
    for name_id, text in names.items():
        table.setName(text, name_id, 3, 1, 0x409)
    for record in table.names:
        if "d2coding" in str(record).lower() and record.nameID not in NOTICES:
            raise SystemExit(f"reserved name left in name ID {record.nameID}: {record}")
    font["head"].modified = timestampFromString(time.asctime(time.gmtime()))
    font.save(output)
    print(f"{output}: {full_name}, {len(font.getGlyphOrder())} glyphs")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("family")
    parser.add_argument("changes", help="the modifications, for the font's description")
    args = parser.parse_args()
    rename(args.source, args.output, args.family, args.changes)


if __name__ == "__main__":
    main()
