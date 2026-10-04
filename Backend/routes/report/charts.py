"""Inline SVG charts for the investor report PDF.

Only charts that need real geometry live here (ring, market circles, positioning
map, radar). Bars, matrices and heatmaps are plain HTML/CSS in the template so
their text wraps. Colours are CSS variables defined in report.css.
"""

import math
from html import escape

from schemas.report import Figure, Positioning, Score


def _f(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def score_ring(score: int, size: int = 132, stroke: int = 12, label: str = "Readiness") -> str:
    score = max(0, min(100, int(score)))
    radius = (size - stroke) / 2
    circumference = 2 * math.pi * radius
    filled = circumference * score / 100
    centre = size / 2
    return f"""
<svg class="ring" viewBox="0 0 {size} {size}" width="{size}" height="{size}" role="img" aria-label="{label} {score} out of 100">
  <circle cx="{centre}" cy="{centre}" r="{_f(radius)}" fill="none" stroke="var(--ring-track)" stroke-width="{stroke}"/>
  <circle cx="{centre}" cy="{centre}" r="{_f(radius)}" fill="none" stroke="url(#ringGrad)" stroke-width="{stroke}"
          stroke-linecap="round" stroke-dasharray="{_f(filled)} {_f(circumference)}"
          transform="rotate(-90 {centre} {centre})"/>
  <defs><linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="var(--accent-2)"/><stop offset="1" stop-color="var(--accent)"/>
  </linearGradient></defs>
  <text x="{centre}" y="{centre + 4}" text-anchor="middle" class="ring-num">{score}</text>
  <text x="{centre}" y="{centre + 24}" text-anchor="middle" class="ring-label">{escape(label.upper())}</text>
</svg>"""


def tam_circles(tam: Figure, sam: Figure, som: Figure, width: int = 330, height: int = 250) -> str:
    """Nested circles sharing a bottom edge. Radii follow sqrt(value) when known,
    clamped so SOM stays visible; unknown figures draw as dashed ghosts."""
    figures = [("TAM", tam, "var(--tam-1)"), ("SAM", sam, "var(--tam-2)"), ("SOM", som, "var(--tam-3)")]
    max_r = height / 2 - 4
    known = [fig.value_usd for _, fig, _ in figures if fig.value_usd]
    top = max(known) if known else 1
    default_ratio = [1.0, 0.66, 0.36]
    radii = []
    for index, (_, fig, _) in enumerate(figures):
        if fig.value_usd and known:
            ratio = math.sqrt(fig.value_usd / top)
            ratio = max(ratio, 0.22 if index == 2 else 0.4)
        else:
            ratio = default_ratio[index]
        if radii:
            ratio = min(ratio, radii[-1] / max_r - 0.08)
        radii.append(max_r * ratio)

    cx = max_r + 4
    bottom = height - 4
    shapes, labels = [], []
    for index, ((name, fig, colour), radius) in enumerate(zip(figures, radii)):
        cy = bottom - radius
        dashed = "" if fig.value_usd else ' stroke-dasharray="4 4" fill-opacity="0.25"'
        shapes.append(
            f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(radius)}" fill="{colour}" '
            f'stroke="var(--paper)" stroke-width="2"{dashed}/>'
        )
        # label anchored at the top of each circle, leader line to the right column
        anchor_y = bottom - 2 * radius + 14
        labels.append(
            f'<text x="{_f(cx)}" y="{_f(anchor_y + 4)}" text-anchor="middle" class="tam-in">{name}</text>'
        )
        lx = 2 * max_r + 22
        ly = 26 + index * 74
        labels.append(
            f'<path d="M{_f(cx + radius * 0.55)} {_f(anchor_y)} L{_f(lx - 8)} {ly - 4}" class="leader"/>'
            f'<text x="{lx}" y="{ly - 10}" class="tam-key">{name}</text>'
            f'<text x="{lx}" y="{ly + 12}" class="tam-val">{escape(fig.display or "Not found")}</text>'
            f'<text x="{lx}" y="{ly + 28}" class="tam-sub">{escape((fig.method or "").title())}'
            f'{" · " + fig.confidence + " confidence" if fig.value_usd else ""}</text>'
        )
    total_w = 2 * max_r + 22 + 130
    return (
        f'<svg class="tam" viewBox="0 0 {_f(max(width, total_w))} {height}" role="img" '
        f'aria-label="Market size: TAM {escape(tam.display)}, SAM {escape(sam.display)}, SOM {escape(som.display)}">'
        + "".join(shapes)
        + "".join(labels)
        + "</svg>"
    )


def positioning_map(positioning: Positioning, size: int = 300) -> str:
    pad_l, pad_b, pad_t, pad_r = 26, 26, 10, 10
    plot = size - pad_l - pad_r
    plot_h = size - pad_t - pad_b
    x0, y0 = pad_l, pad_t

    def px(value: int) -> float:
        return x0 + plot * value / 100

    def py(value: int) -> float:
        return y0 + plot_h * (1 - value / 100)

    parts = [
        f'<rect x="{x0}" y="{y0}" width="{plot}" height="{plot_h}" class="pm-bg"/>',
        f'<rect x="{_f(px(50))}" y="{y0}" width="{_f(plot / 2)}" height="{_f(plot_h / 2)}" class="pm-best"/>',
        f'<line x1="{_f(px(50))}" y1="{y0}" x2="{_f(px(50))}" y2="{y0 + plot_h}" class="pm-mid"/>',
        f'<line x1="{x0}" y1="{_f(py(50))}" x2="{x0 + plot}" y2="{_f(py(50))}" class="pm-mid"/>',
        # axis end labels
        f'<text x="{x0}" y="{size - 8}" class="pm-end">{escape(positioning.x_axis.low)}</text>',
        f'<text x="{x0 + plot}" y="{size - 8}" text-anchor="end" class="pm-end">{escape(positioning.x_axis.high)} →</text>',
        f'<text x="{_f(x0 + plot / 2)}" y="{size - 8}" text-anchor="middle" class="pm-axis">{escape(positioning.x_axis.label)}</text>',
        f'<text transform="translate(12 {y0 + plot_h}) rotate(-90)" class="pm-end">{escape(positioning.y_axis.low)}</text>',
        f'<text transform="translate(12 {y0}) rotate(-90)" text-anchor="end" class="pm-end">{escape(positioning.y_axis.high)} →</text>',
        f'<text transform="translate(12 {_f(y0 + plot_h / 2)}) rotate(-90)" text-anchor="middle" class="pm-axis">{escape(positioning.y_axis.label)}</text>',
    ]
    # draw competitors first so "us" sits on top
    ordered = sorted(enumerate(positioning.points, start=1), key=lambda item: item[1].is_us)
    marks, labels = [], []
    dots = [(px(point.x), py(point.y)) for _, point in ordered]
    placed: list[tuple[float, float, float, float]] = []
    for number, point in ordered:
        cx, cy = px(point.x), py(point.y)
        if point.is_us:
            marks.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="15" class="pm-halo"/>')
            marks.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="8" class="pm-us"/>')
        else:
            marks.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="7" class="pm-dot"/>')
            marks.append(f'<text x="{_f(cx)}" y="{_f(cy + 3)}" text-anchor="middle" class="pm-num">{number}</text>')
        x, y, anchor, box = _place_label(cx, cy, point.name, placed, dots, x0, y0, plot, plot_h)
        placed.append(box)
        labels.append(
            f'<text x="{_f(x)}" y="{_f(y)}" text-anchor="{anchor}" '
            f'class="{"pm-label-us" if point.is_us else "pm-label"}">{escape(point.name)}</text>'
        )
    parts += marks + labels
    return (
        f'<svg class="pm" viewBox="0 0 {size} {size}" role="img" aria-label="Positioning map: '
        f'{escape(positioning.x_axis.label)} against {escape(positioning.y_axis.label)}">'
        + "".join(parts)
        + "</svg>"
    )


def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _place_label(cx, cy, name, placed, dots, x0, y0, plot, plot_h):
    """Try label positions around a dot; keep the first that hits no label or dot."""
    width = len(name) * 5.4 + 6
    candidates = [(12, -9, "start"), (-12, -9, "end"), (12, 13, "start"), (-12, 13, "end"),
                  (0, -14, "middle"), (0, 20, "middle"), (12, 2, "start"), (-12, 2, "end")]
    best = None
    for dx, dy, anchor in candidates:
        x, y = cx + dx, cy + dy
        left = x if anchor == "start" else x - width if anchor == "end" else x - width / 2
        box = (left, y - 8, left + width, y + 2)
        inside = box[0] >= x0 - 2 and box[2] <= x0 + plot + 2 and box[1] >= y0 and box[3] <= y0 + plot_h
        clash = any(_overlaps(box, other) for other in placed) or any(
            _overlaps(box, (dx_ - 8, dy_ - 8, dx_ + 8, dy_ + 8)) for dx_, dy_ in dots if (dx_, dy_) != (cx, cy)
        )
        if inside and not clash:
            return x, y, anchor, box
        if best is None and inside:
            best = (x, y, anchor, box)
    return best or (cx + 12, cy - 9, "start", (cx + 12, cy - 17, cx + 12 + width, cy - 7))


def radar(scores: list[Score], size: int = 260, max_score: int = 10) -> str:
    count = len(scores)
    if count < 3:
        return ""
    centre = size / 2
    radius = size / 2 - 44

    def point(index: int, value: float) -> tuple[float, float]:
        angle = -math.pi / 2 + 2 * math.pi * index / count
        r = radius * value / max_score
        return centre + r * math.cos(angle), centre + r * math.sin(angle)

    rings = []
    for level in (2, 4, 6, 8, 10):
        pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in (point(i, level) for i in range(count)))
        rings.append(f'<polygon points="{pts}" class="rd-ring"/>')
    spokes = "".join(
        f'<line x1="{centre}" y1="{centre}" x2="{_f(x)}" y2="{_f(y)}" class="rd-spoke"/>'
        for x, y in (point(i, max_score) for i in range(count))
    )
    shape = " ".join(f"{_f(x)},{_f(y)}" for x, y in (point(i, s.score) for i, s in enumerate(scores)))
    dots = "".join(
        f'<circle cx="{_f(x)}" cy="{_f(y)}" r="4" class="rd-dot"/>'
        for x, y in (point(i, s.score) for i, s in enumerate(scores))
    )
    labels = []
    for index, score in enumerate(scores):
        x, y = point(index, max_score + 2.6)
        anchor = "middle" if abs(x - centre) < 8 else ("start" if x > centre else "end")
        labels.append(
            f'<text x="{_f(x)}" y="{_f(y)}" text-anchor="{anchor}" class="rd-label">{escape(score.dimension)}'
            f'<tspan class="rd-val" dx="4">{score.score}</tspan></text>'
        )
    return (
        f'<svg class="radar" viewBox="0 0 {size} {size}" role="img" aria-label="Scorecard: '
        + ", ".join(f"{escape(s.dimension)} {s.score}" for s in scores)
        + '">'
        + "".join(rings)
        + spokes
        + f'<polygon points="{shape}" class="rd-shape"/>'
        + dots
        + "".join(labels)
        + "</svg>"
    )
