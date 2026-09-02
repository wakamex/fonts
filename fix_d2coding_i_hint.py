#!/usr/bin/env python3
"""Add D2Coding's missing lowercase-i hint correction at 18 ppem."""

import argparse
import os
import stat
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont


def delta_program(point: int, include_18_ppem: bool) -> list[str]:
    ppem_deltas = [144, 160, 176] if include_18_ppem else [160, 176]
    values = [value for delta in ppem_deltas for value in (delta, point)]
    return [
        f"NPUSHW[ ]\t/* {len(values) + 1} values pushed */",
        *(str(value) for value in values),
        str(len(ppem_deltas)),
    ]


def replace_once(program: list[str], old: list[str], new: list[str]) -> bool:
    matches = [
        index
        for index in range(len(program) - len(old) + 1)
        if program[index : index + len(old)] == old
    ]
    if not matches:
        return False
    if len(matches) != 1:
        raise ValueError(f"expected one hint sequence, found {len(matches)}")
    index = matches[0]
    program[index : index + len(old)] = new
    return True


def patch_font(path: Path, check: bool) -> bool:
    font = TTFont(path, lazy=True, recalcBBoxes=False, recalcTimestamp=False)
    glyf = font["glyf"]
    if "i" not in glyf:
        raise ValueError("font has no lowercase i")

    glyph = glyf["i"]
    program = glyph.program.getAssembly()
    changed = False

    for point in (2, 5):
        old = delta_program(point, include_18_ppem=False)
        fixed = delta_program(point, include_18_ppem=True)
        if replace_once(program, old, fixed):
            changed = True
        elif not any(
            program[index : index + len(fixed)] == fixed
            for index in range(len(program) - len(fixed) + 1)
        ):
            raise ValueError(f"lowercase i does not contain the expected point-{point} hint sequence")

    if check:
        if changed:
            font.close()
            raise ValueError("missing the 18 ppem lowercase-i hint correction")
        font.close()
        print(f"ok {path}")
        return False

    if not changed:
        font.close()
        print(f"unchanged {path}")
        return False

    glyph.program.fromAssembly(program)
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
