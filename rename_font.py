"""Rename a modified D2Coding build and give it D2Coding 1.3.3's credits.

D2Coding's OFL 1.1 reserves the name "D2Coding", so modified builds carry another family
name. D2Coding 1.3.3 changed only metadata from 1.3.2 (NAVER instead of NHN in the
credits, a current license URL), so applying those records here makes a 1.3.2-based build
match a 1.3.3-based one. Every other name record, including Korean and Mac ones that
repeated the old name, is dropped.

    uv run --with fonttools --with brotli python rename_font.py SOURCE OUTPUT FAMILY CHANGES
"""

import argparse
from pathlib import Path
import time

from fontTools.ttLib import TTFont
from fontTools.misc.timeTools import timestampFromString

UPSTREAM = {
    0: "Copyright (c) 2015-2016 NAVER Corporation. All rights reserved. "
       "Font designed by FONTRIX Inc.",
    7: "D2Coding ligature is a registered trademark of NAVER Corporation.",
    8: "NAVER Corporation",
    9: "Yong-Rak Park; Jeong-Hwan Yoon; Sang-Min Lee;",
    11: "https://www.navercorp.com",
    12: "http://fontrix.co.kr",
    13: "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
    14: "https://openfontlicense.org",
}
UPSTREAM_VERSION = "Version 1.3.3; Build 20260725"
UPSTREAM_REVISION = 1.0030059814453125
# Copyright, trademark, and license notices may name the original font.
NOTICES = {0, 7, 10, 13, 14}


def rename(source: Path, output: Path, family: str, changes: str) -> None:
    font = TTFont(source)
    names = {
        **UPSTREAM,
        1: family,
        2: "Regular",
        3: f"{family} Regular",
        4: family,
        5: f"{UPSTREAM_VERSION}; modified",
        6: f"{family.replace(' ', '')}-Regular",
        10: f"Modified from the D2Coding 1.3.3 ligature font by NAVER Corporation: {changes}.",
    }
    table = font["name"]
    table.names = []
    for name_id, text in names.items():
        table.setName(text, name_id, 3, 1, 0x409)
    for record in table.names:
        if "d2coding" in str(record).lower() and record.nameID not in NOTICES:
            raise SystemExit(f"reserved name left in name ID {record.nameID}: {record}")
    font["head"].fontRevision = UPSTREAM_REVISION
    font["head"].modified = timestampFromString(time.asctime(time.gmtime()))
    font.save(output)
    print(f"{output}: {family}, {len(font.getGlyphOrder())} glyphs")


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
