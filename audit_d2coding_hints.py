#!/usr/bin/env python3
"""Find isolated baseline lifts associated with a missing TrueType delta hint."""

import argparse
import hashlib
import html
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import freetype
from fontTools.ttLib import TTFont

DEFAULT_PPEM = 18
DEFAULT_DELTA_BASE = 9
DEFAULT_DELTA_SHIFT = 3
NEIGHBOR_OFFSETS = (-2, -1, 0, 1, 2)


@dataclass(frozen=True)
class DeltaGap:
    point: int
    low_nibble: int

    def amount_px(self, delta_shift: int) -> float:
        step = self.low_nibble - (7 if self.low_nibble >= 8 else 8)
        return step / (1 << delta_shift)


@dataclass(frozen=True)
class RasterMetrics:
    ppem: int
    bottom: int
    top: int
    rows: int
    left: int
    width: int
    advance: int
    pixels: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class Finding:
    glyph_name: str
    codepoints: tuple[int, ...]
    metrics: tuple[RasterMetrics, ...]
    gaps: tuple[DeltaGap, ...]


def pushed_delta_pairs(assembly: list[str]) -> Iterable[tuple[str, list[tuple[int, int]]]]:
    for index, operation in enumerate(assembly):
        if not operation.startswith("DELTAP"):
            continue
        start = index - 1
        while start >= 0 and not (
            assembly[start].startswith("PUSH") or assembly[start].startswith("NPUSH")
        ):
            start -= 1
        if start < 0:
            continue
        try:
            values = [int(value) for value in assembly[start + 1 : index]]
        except ValueError:
            continue
        if not values:
            continue
        count = values[-1]
        operands = values[:-1]
        if len(operands) != count * 2:
            continue
        yield operation.split("[")[0], list(zip(operands[::2], operands[1::2]))


def delta_ppem(operation: str, packed: int, delta_base: int) -> int:
    range_offset = {"DELTAP1": 0, "DELTAP2": 16, "DELTAP3": 32}[operation]
    return delta_base + range_offset + (packed >> 4)


def find_delta_gaps(
    font: TTFont, target_ppem: int, delta_base: int
) -> dict[str, tuple[DeltaGap, ...]]:
    gaps: dict[str, tuple[DeltaGap, ...]] = {}
    for glyph_name in font.getGlyphOrder():
        glyph = font["glyf"][glyph_name]
        program = getattr(glyph, "program", None)
        if not program:
            continue
        by_point: dict[int, set[tuple[int, int]]] = defaultdict(set)
        for operation, pairs in pushed_delta_pairs(program.getAssembly()):
            for packed, point in pairs:
                by_point[point].add(
                    (delta_ppem(operation, packed, delta_base), packed & 0x0F)
                )
        glyph_gaps = []
        for point, deltas in by_point.items():
            for low_nibble in range(16):
                if (
                    (target_ppem + 1, low_nibble) in deltas
                    and (target_ppem + 2, low_nibble) in deltas
                    and (target_ppem, low_nibble) not in deltas
                ):
                    glyph_gaps.append(DeltaGap(point, low_nibble))
        if glyph_gaps:
            gaps[glyph_name] = tuple(sorted(glyph_gaps, key=lambda gap: gap.point))
    return gaps


def render_glyph(face: freetype.Face, codepoint: int, ppem: int) -> RasterMetrics:
    face.set_pixel_sizes(0, ppem)
    face.load_char(
        chr(codepoint), freetype.FT_LOAD_DEFAULT | freetype.FT_LOAD_RENDER
    )
    glyph = face.glyph
    bitmap = glyph.bitmap
    if bitmap.pixel_mode != freetype.FT_PIXEL_MODE_GRAY:
        raise ValueError(
            f"unsupported FreeType pixel mode {bitmap.pixel_mode} for U+{codepoint:04X}"
        )
    pitch = abs(bitmap.pitch)
    raw = bytes(bitmap.buffer)
    rows = []
    for row in range(bitmap.rows):
        source_row = bitmap.rows - row - 1 if bitmap.pitch < 0 else row
        start = source_row * pitch
        rows.append(tuple(raw[start : start + bitmap.width]))
    return RasterMetrics(
        ppem=ppem,
        bottom=glyph.bitmap_top - bitmap.rows,
        top=glyph.bitmap_top,
        rows=bitmap.rows,
        left=glyph.bitmap_left,
        width=bitmap.width,
        advance=round(glyph.advance.x / 64),
        pixels=tuple(rows),
    )


def is_isolated_baseline_lift(metrics: tuple[RasterMetrics, ...]) -> bool:
    center = len(metrics) // 2
    return (
        metrics[center].bottom > 0
        and metrics[center - 1].bottom <= 0
        and metrics[center + 1].bottom <= 0
    )


def glyph_svg(metric: RasterMetrics, all_metrics: tuple[RasterMetrics, ...]) -> str:
    max_ppem = max(sample.ppem for sample in all_metrics)
    baseline = max_ppem + 5
    width = max(12, max(sample.advance for sample in all_metrics) + 8)
    height = baseline + 7
    rectangles = []
    for row, pixels in enumerate(metric.pixels):
        for column, coverage in enumerate(pixels):
            if not coverage:
                continue
            x = 4 + metric.left + column
            y = baseline - metric.top + row
            rectangles.append(
                f'<rect x="{x}" y="{y}" width="1" height="1" opacity="{coverage / 255:.3f}"/>'
            )
    return (
        f'<svg class="glyph" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{metric.ppem} ppem raster, bottom {metric.bottom}">'
        f'<line class="baseline" x1="0" y1="{baseline + 0.5}" x2="{width}" y2="{baseline + 0.5}"/>'
        f'<g>{"".join(rectangles)}</g></svg>'
    )


def codepoint_label(codepoints: tuple[int, ...]) -> str:
    return ", ".join(f"U+{codepoint:04X}" for codepoint in codepoints)


def finding_html(
    finding: Finding, delta_shift: int, confirmed: bool
) -> str:
    codepoint = finding.codepoints[0]
    character = html.escape(chr(codepoint))
    unicode_name = unicodedata.name(chr(codepoint), "Unassigned")
    target_ppem = finding.metrics[len(finding.metrics) // 2].ppem
    samples = []
    for metric in finding.metrics:
        class_name = "sample target" if metric.ppem == target_ppem else "sample"
        samples.append(
            f'<figure class="{class_name}">{glyph_svg(metric, finding.metrics)}'
            f'<figcaption>{metric.ppem} ppem<br><code>bottom={metric.bottom}</code></figcaption></figure>'
        )
    if finding.gaps:
        gap_parts = []
        for gap in finding.gaps:
            amount = gap.amount_px(delta_shift)
            gap_parts.append(
                f"point {gap.point}: {amount:g} px at {target_ppem + 1} and {target_ppem + 2} ppem"
            )
        evidence = "; ".join(gap_parts) + f", absent at {target_ppem} ppem"
    else:
        evidence = "No matching 19/20 delta gap. This raster anomaly needs separate inspection."
    classification = "Confirmed delta-gap match" if confirmed else "Raster-only review candidate"
    return f"""
    <article class="finding">
      <header>
        <span class="character">{character}</span>
        <div><h3>{html.escape(finding.glyph_name)}</h3><p>{codepoint_label(finding.codepoints)} - {html.escape(unicode_name)}</p></div>
        <span class="classification">{classification}</span>
      </header>
      <div class="samples">{"".join(samples)}</div>
      <p class="evidence">{html.escape(evidence)}</p>
    </article>
    """.strip() + "\n"


def report_html(
    font_path: Path,
    font: TTFont,
    target_ppem: int,
    delta_base: int,
    delta_shift: int,
    static_candidate_count: int,
    confirmed: list[Finding],
    review: list[Finding],
) -> str:
    name_table = font["name"]
    family = name_table.getDebugName(1) or "Unknown"
    version = name_table.getDebugName(5) or "Unknown"
    digest = hashlib.sha256(font_path.read_bytes()).hexdigest()
    confirmed_markup = "".join(
        finding_html(finding, delta_shift, True) for finding in confirmed
    ) or "<p>No confirmed findings.</p>"
    review_markup = "".join(
        finding_html(finding, delta_shift, False) for finding in review
    ) or "<p>No additional raster-only candidates.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>D2Coding native-hint audit</title>
<style>
:root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
body {{ max-width: 1100px; margin: 0 auto; padding: 32px; background: #f2f0ea; color: #171717; }}
h1, h2, h3, p {{ margin-top: 0; }}
code {{ font-family: ui-monospace, monospace; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 24px 0; }}
.summary div, .finding {{ background: #fff; border: 1px solid #c9c5ba; box-shadow: 0 2px 0 #d7d2c5; }}
.summary div {{ padding: 14px; }}
.summary strong {{ display: block; font-size: 1.5rem; }}
.metadata {{ overflow-wrap: anywhere; }}
.finding {{ margin: 18px 0; padding: 18px; }}
.finding header {{ display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 16px; }}
.finding h3, .finding header p {{ margin: 0; }}
.character {{ display: grid; place-items: center; width: 56px; height: 56px; font: 32px serif; background: #ece8dc; border: 1px solid #c9c5ba; }}
.classification {{ padding: 5px 8px; background: #f7df78; border: 1px solid #8b7413; font-size: .8rem; }}
.samples {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0 12px; }}
.sample {{ margin: 0; text-align: center; }}
.sample.target {{ background: #fff2ef; outline: 2px solid #c9342f; }}
.sample.target figcaption {{ color: #171717; }}
.glyph {{ display: block; width: 150px; height: 190px; background: #fafafa; shape-rendering: crispEdges; }}
.glyph rect {{ fill: #111; }}
.baseline {{ stroke: #d02b26; stroke-width: .16; stroke-dasharray: .7 .4; }}
figcaption {{ padding: 5px; font-size: .82rem; }}
.evidence {{ margin-bottom: 0; font-family: ui-monospace, monospace; }}
@media (prefers-color-scheme: dark) {{
  body {{ background: #171717; color: #eee; }}
  .summary div, .finding {{ background: #242424; border-color: #555; box-shadow: 0 2px 0 #000; }}
  .character {{ background: #303030; border-color: #555; }}
  .glyph {{ background: #f7f7f7; }}
  .classification {{ color: #171717; }}
}}
</style>
</head>
<body>
<h1>D2Coding native-hint audit</h1>
<p>The confirmed set intersects two independent signals: a glyph applies the same point delta at {target_ppem + 1} and {target_ppem + 2} ppem but omits {target_ppem}, and its native FreeType raster rises above the baseline only at {target_ppem} ppem.</p>
<div class="summary">
  <div><strong>{static_candidate_count}</strong>glyphs with a static delta gap</div>
  <div><strong>{len(confirmed)}</strong>confirmed baseline lifts</div>
  <div><strong>{len(review)}</strong>raster-only review candidates</div>
</div>
<p class="metadata"><code>{html.escape(font_path.name)}</code><br>{html.escape(family)} - {html.escape(version)}<br>SHA-256 <code>{digest}</code><br>FreeType {html.escape(".".join(map(str, freetype.version())))}; delta base {delta_base}; delta shift {delta_shift}</p>
<p class="metadata">Reproduce with <code>uv run --with fonttools --with freetype-py python audit_d2coding_hints.py {html.escape(font_path.name)} --output hint-audit.html</code></p>
<h2>Confirmed delta-gap matches</h2>
{confirmed_markup}
<h2>Additional isolated baseline lifts</h2>
{review_markup}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path)
    parser.add_argument("--output", type=Path, default=Path("d2coding-hint-audit.html"))
    parser.add_argument("--ppem", type=int, default=DEFAULT_PPEM)
    parser.add_argument("--delta-base", type=int, default=DEFAULT_DELTA_BASE)
    parser.add_argument("--delta-shift", type=int, default=DEFAULT_DELTA_SHIFT)
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    font = TTFont(args.font)
    cmap = font.getBestCmap()
    if not cmap:
        raise SystemExit("font has no Unicode cmap")
    codepoints_by_glyph: dict[str, list[int]] = defaultdict(list)
    for codepoint, glyph_name in cmap.items():
        codepoints_by_glyph[glyph_name].append(codepoint)

    static_gaps = find_delta_gaps(font, args.ppem, args.delta_base)
    face = freetype.Face(str(args.font))
    ppems = tuple(args.ppem + offset for offset in NEIGHBOR_OFFSETS)
    raster_lifts: dict[str, tuple[RasterMetrics, ...]] = {}
    for glyph_name, codepoints in codepoints_by_glyph.items():
        metrics = tuple(render_glyph(face, codepoints[0], ppem) for ppem in ppems)
        if is_isolated_baseline_lift(metrics):
            raster_lifts[glyph_name] = metrics

    confirmed = []
    review = []
    for glyph_name, metrics in raster_lifts.items():
        finding = Finding(
            glyph_name=glyph_name,
            codepoints=tuple(codepoints_by_glyph[glyph_name]),
            metrics=metrics,
            gaps=static_gaps.get(glyph_name, ()),
        )
        (confirmed if finding.gaps else review).append(finding)
    confirmed.sort(key=lambda finding: finding.codepoints[0])
    review.sort(key=lambda finding: finding.codepoints[0])

    report = report_html(
        args.font,
        font,
        args.ppem,
        args.delta_base,
        args.delta_shift,
        len(static_gaps),
        confirmed,
        review,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(
        f"{len(confirmed)} confirmed, {len(review)} review candidates; wrote {args.output}"
    )
    if args.fail_on_findings and confirmed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
