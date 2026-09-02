#!/usr/bin/env python3
"""Add D2Coding's missing lowercase-i-family hint corrections at 18 ppem."""

import argparse
import os
import stat
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont

REPAIRS = {
    "i": (2, 5),
    "uni0456": (2, 5),
    "uni045D": (9, 16),
}


def delta_blocks(program: list[str]):
    for end, operation in enumerate(program):
        if not operation.startswith("DELTAP1"):
            continue
        start = end - 1
        while start >= 0 and not (
            program[start].startswith("PUSH") or program[start].startswith("NPUSH")
        ):
            start -= 1
        if start < 0:
            continue
        try:
            values = [int(value) for value in program[start + 1 : end]]
        except ValueError:
            continue
        if not values or len(values[:-1]) != values[-1] * 2:
            continue
        yield start, end, list(zip(values[:-1:2], values[1:-1:2]))


def add_18_ppem_delta(program: list[str], point: int) -> bool:
    for start, end, pairs in delta_blocks(program):
        if (144, point) in pairs:
            return False
        if (160, point) not in pairs or (176, point) not in pairs:
            continue
        insertion = pairs.index((160, point))
        pairs.insert(insertion, (144, point))
        values = [value for pair in pairs for value in pair]
        program[start:end] = [
            f"NPUSHW[ ]\t/* {len(values) + 1} values pushed */",
            *(str(value) for value in values),
            str(len(pairs)),
        ]
        return True
    raise ValueError(f"point {point} does not contain the expected 19/20 ppem hint sequence")


def patch_font(path: Path, check: bool) -> bool:
    font = TTFont(path, lazy=True, recalcBBoxes=False, recalcTimestamp=False)
    glyf = font["glyf"]
    if "i" not in glyf:
        raise ValueError("font has no lowercase i")

    changed = False
    for glyph_name, points in REPAIRS.items():
        if glyph_name not in glyf:
            continue
        glyph = glyf[glyph_name]
        program = glyph.program.getAssembly()
        glyph_changed = False
        for point in points:
            glyph_changed |= add_18_ppem_delta(program, point)
        if glyph_changed:
            glyph.program.fromAssembly(program)
            changed = True

    if check:
        if changed:
            font.close()
            raise ValueError("missing an 18 ppem lowercase-i-family hint correction")
        font.close()
        print(f"ok {path}")
        return False

    if not changed:
        font.close()
        print(f"unchanged {path}")
        return False

    # Loading glyf may load post to establish the glyph order. Preserve the
    # original post bytes instead of needlessly normalizing that table.
    if "post" in font.tables:
        del font.tables["post"]
    original_mode = stat.S_IMODE(path.stat().st_mode)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        try:
            font.save(temporary_path, reorderTables=False)
        finally:
            font.close()
        temporary_path.chmod(original_mode)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)

    print(f"patched {path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the correction without changing files")
    parser.add_argument("fonts", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.fonts:
        try:
            patch_font(path, args.check)
        except (KeyError, OSError, ValueError) as error:
            failed = True
            print(f"error {path}: {error}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
