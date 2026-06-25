"""Charts and competitor visuals for the investor one-pager."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path

from fpdf import FPDF

from schemas.teardown import CompetitorItem, CustomerVoiceAnalysis, ProductTeardown

LOGO_CACHE_DIR = Path(__file__).parent / "assets" / "logo_cache"
LOGO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

NAVY = (15, 32, 68)
DEEP_BLUE = (30, 64, 120)
ACCENT = (232, 93, 44)
ACCENT_SOFT = (255, 247, 242)
MID_GREY = (100, 116, 139)
DARK_TEXT = (30, 41, 59)
WHITE = (255, 255, 255)
LIGHT_BG = (248, 250, 252)
PANEL_BORDER = (226, 232, 240)

AVATAR_COLORS = [
    (30, 64, 120),
    (232, 93, 44),
    (22, 101, 52),
    (124, 58, 237),
    (219, 39, 119),
]


def _sanitize_domain(raw: str) -> str:
    domain = raw.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0].removeprefix("www.")
    return domain


def fetch_logo(domain: str) -> Path | None:
    """Download Clearbit logo into cache; return path or None."""
    domain = _sanitize_domain(domain)
    if not domain or "." not in domain:
        return None

    cache_path = LOGO_CACHE_DIR / f"{domain.replace('.', '_')}.png"
    if cache_path.exists() and cache_path.stat().st_size > 200:
        return cache_path

    url = f"https://logo.clearbit.com/{domain}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ShipIt/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = resp.read()
        if len(data) < 200:
            return None
        cache_path.write_bytes(data)
        return cache_path
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


def satisfaction_score(summary: str) -> float:
    s = summary.lower()
    if "high" in s:
        return 0.82
    if "low" in s:
        return 0.22
    if "mixed" in s:
        return 0.52
    return 0.45


def capability_score(name: str, why: str, features: list[str]) -> float:
    blob = f"{name} {why} {' '.join(features)}".lower()
    keywords = ("ai", "predict", "forecast", "automated", "machine", "smart", "intelligent")
    hits = sum(1 for kw in keywords if kw in blob)
    return min(0.92, 0.28 + hits * 0.16)


def _sentiment_map(voice: CustomerVoiceAnalysis) -> dict[str, str]:
    return {s.name.lower(): s.satisfaction_summary for s in voice.competitor_sentiment}


def draw_panel(pdf: FPDF, x: float, y: float, w: float, h: float):
    pdf.set_fill_color(*LIGHT_BG)
    pdf.set_draw_color(*PANEL_BORDER)
    pdf.set_line_width(0.3)
    pdf.rect(x, y, w, h, style="DF")


def draw_letter_avatar(pdf: FPDF, x: float, y: float, size: float, letter: str, color_index: int):
    color = AVATAR_COLORS[color_index % len(AVATAR_COLORS)]
    pdf.set_fill_color(*color)
    pdf.rect(x, y, size, size, "F")
    pdf.set_xy(x, y + size * 0.28)
    pdf.set_font("Helvetica", "B", size * 2.2)
    pdf.set_text_color(*WHITE)
    pdf.cell(size, size * 0.5, letter.upper(), align="C")


def draw_competitor_row(
    pdf: FPDF,
    x: float,
    y: float,
    w: float,
    competitors: list[CompetitorItem],
    limit: int = 3,
) -> float:
    """Logo or letter avatar + name for each competitor."""
    items = competitors[:limit]
    if not items:
        return y

    slot_w = w / len(items)
    icon = 10.0

    for i, comp in enumerate(items):
        cx = x + i * slot_w + (slot_w - icon) / 2
        logo_path = fetch_logo(comp.website) if comp.website else None

        if logo_path:
            try:
                pdf.image(str(logo_path), x=cx, y=y, w=icon, h=icon)
            except Exception:
                draw_letter_avatar(pdf, cx, y, icon, comp.name[:1], i)
        else:
            draw_letter_avatar(pdf, cx, y, icon, comp.name[:1], i)

        pdf.set_xy(x + i * slot_w, y + icon + 1)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(*DARK_TEXT)
        name = comp.name[:18] + ("..." if len(comp.name) > 18 else "")
        pdf.cell(slot_w, 3, name, align="C")

    return y + icon + 5


def draw_positioning_matrix(
    pdf: FPDF,
    x: float,
    y: float,
    w: float,
    h: float,
    product_name: str,
    teardown: ProductTeardown,
) -> float:
    """
    2x2 value-positioning map:
      X = AI / capability    Y = customer satisfaction (from voice research)
    """
    draw_panel(pdf, x, y, w, h)

    pad = 4.0
    plot_x = x + pad + 14
    plot_y = y + pad + 6
    plot_w = w - 2 * pad - 16
    plot_h = h - 2 * pad - 10

    pdf.set_xy(x + pad, y + 2)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*DEEP_BLUE)
    pdf.cell(w - 2 * pad, 4, "VALUE POSITIONING MAP", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(*PANEL_BORDER)
    pdf.set_line_width(0.25)
    pdf.line(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h)
    pdf.line(plot_x, plot_y, plot_x, plot_y + plot_h)

    mid_x = plot_x + plot_w / 2
    mid_y = plot_y + plot_h / 2
    pdf.set_draw_color(230, 235, 240)
    pdf.line(mid_x, plot_y, mid_x, plot_y + plot_h)
    pdf.line(plot_x, mid_y, plot_x + plot_w, mid_y)

    pdf.set_font("Helvetica", "", 5.5)
    pdf.set_text_color(*MID_GREY)
    pdf.set_xy(plot_x, plot_y - 4)
    pdf.cell(plot_w, 3, "Customer satisfaction", align="C")
    pdf.set_xy(plot_x - 13, plot_y + plot_h / 2)
    pdf.cell(12, 3, "AI", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "I", 5)
    pdf.set_xy(plot_x + 1, plot_y + 1)
    pdf.cell(20, 2, "incumbents")
    pdf.set_xy(plot_x + plot_w - 22, plot_y + 1)
    pdf.cell(22, 2, "high satisfaction", align="R")
    pdf.set_xy(plot_x + plot_w - 18, plot_y + plot_h - 3)
    pdf.cell(18, 2, "AI leaders", align="R")

    sentiments = _sentiment_map(teardown.customer_voice)
    features = teardown.core_features + teardown.customer_voice.recommended_features

    points: list[tuple[str, float, float, bool]] = []
    for comp in teardown.competitors[:3]:
        sat = satisfaction_score(sentiments.get(comp.name.lower(), "unknown"))
        cap = capability_score(comp.name, comp.why_competes, features)
        points.append((comp.name, cap, sat, False))

    prod_cap = min(0.95, capability_score(product_name, teardown.one_liner, features) + 0.12)
    prod_sat = min(0.92, 0.62 + len(teardown.customer_voice.market_gaps) * 0.08)
    points.append((product_name, prod_cap, prod_sat, True))

    for name, cap, sat, is_product in points:
        px = plot_x + cap * plot_w
        py = plot_y + plot_h - sat * plot_h
        r = 2.2 if is_product else 1.6
        if is_product:
            pdf.set_fill_color(*ACCENT)
            pdf.set_draw_color(*NAVY)
            pdf.set_line_width(0.5)
        else:
            pdf.set_fill_color(*DEEP_BLUE)
            pdf.set_draw_color(*WHITE)
            pdf.set_line_width(0.2)
        pdf.ellipse(px - r, py - r, 2 * r, 2 * r, style="DF")

        pdf.set_font("Helvetica", "B" if is_product else "", 5)
        pdf.set_text_color(*ACCENT if is_product else DARK_TEXT)
        label = name[:14] + ("*" if is_product else "")
        pdf.set_xy(px + 2.5, py - 1.5)
        pdf.cell(30, 2, label)

    return y + h + 2


import math as _math


def _clip_text(text: str, max_chars: int = 35) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1].rsplit(" ", 1)[0] + "..."


def _bullet_line(pdf: FPDF, x: float, y: float, w: float, text: str,
                 dot_color: tuple, font_size: float = 6.0) -> float:
    """Single bullet line — coloured dot + text, no overflow cards."""
    dot_r = 1.0
    pdf.set_fill_color(*dot_color)
    pdf.rect(x, y + font_size * 0.18, dot_r * 2, dot_r * 2, "F")
    pdf.set_xy(x + dot_r * 2 + 2, y)
    pdf.set_font("Helvetica", "", font_size)
    pdf.set_text_color(*DARK_TEXT)
    pdf.cell(w - dot_r * 2 - 2, font_size * 0.6, _clip_text(text, 40))
    return y + font_size * 0.7


def _semicircle_polygon(cx: float, cy: float, r: float, top: bool) -> list[tuple]:
    """Return polygon points for the top or bottom half of a circle."""
    pts = [(cx, cy)]
    steps = 36
    start = 0 if top else _math.pi
    end = _math.pi if top else 2 * _math.pi
    for i in range(steps + 1):
        a = start + (end - start) * i / steps
        pts.append((cx + r * _math.cos(a), cy - r * _math.sin(a)))
    pts.append((cx, cy))
    return pts


def draw_value_proposition_canvas(
    pdf: FPDF,
    x: float,
    y: float,
    w: float,
    h: float,
    gains: list[str],
    pains: list[str],
    jobs: list[str],
) -> float:
    """
    Clean Value Proposition Canvas.

    ┌─── outer panel (w × h) ─────────────────────────────────────────────┐
    │  VALUE PROPOSITION CANVAS        (6mm title bar, navy bg)           │
    ├──────────────────────────────────────────────────────────────────────┤
    │  [   SQUARE  42%  ]  arrow  [      CIRCLE  44%     ]                │
    │  ┌────────────────┐   ──►  ╭──────────────────────╮                 │
    │  │ Gain Creators  │        │  (top) Gains          │                 │
    │  │  • feature 1   │        │   • job / segment 1   │                 │
    │  │  • feature 2   │        ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤                 │
    │  ├────────────────┤        │  (bot) Pains          │                 │
    │  │ Pain Relievers │        │   • pain 1            │                 │
    │  │  • pain 1      │        ╰──────────────────────╯                 │
    │  │  • pain 2      │                                                  │
    │  └────────────────┘                                                  │
    └──────────────────────────────────────────────────────────────────────┘
    """
    GAIN_BG  = (235, 245, 250)
    PAIN_BG  = (255, 244, 237)
    SQ_BORDER = DEEP_BLUE
    CIR_BORDER = DEEP_BLUE

    title_h = 6.0
    pad = 5.0

    # ── Outer panel ────────────────────────────────────────────────
    draw_panel(pdf, x, y, w, h)

    # ── Title bar ──────────────────────────────────────────────────
    pdf.set_fill_color(*NAVY)
    pdf.rect(x, y, w, title_h, "F")
    pdf.set_xy(x, y + 1.2)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*WHITE)
    pdf.cell(w, title_h - 1.2, "VALUE PROPOSITION CANVAS", align="C")

    inner_y = y + title_h + pad
    inner_h = h - title_h - 2 * pad

    # ── Layout geometry ────────────────────────────────────────────
    sq_w  = w * 0.40
    sq_h  = inner_h
    sq_x  = x + pad

    cir_d  = min(w * 0.42, inner_h)        # diameter — keeps circle within height
    cir_bx = x + w - pad - cir_d           # bounding box left edge
    cir_cx = cir_bx + cir_d / 2            # center x
    cir_cy = inner_y + inner_h / 2         # center y
    cir_r  = cir_d / 2

    arrow_x1 = sq_x + sq_w + 2
    arrow_x2 = cir_bx - 2
    arrow_my = inner_y + inner_h / 2

    half_h = sq_h / 2

    # ── Square: top half (Gain Creators) ──────────────────────────
    pdf.set_fill_color(*GAIN_BG)
    pdf.set_draw_color(*SQ_BORDER)
    pdf.set_line_width(0.0)
    pdf.rect(sq_x, inner_y, sq_w, half_h, "F")

    # ── Square: bottom half (Pain Relievers) ──────────────────────
    pdf.set_fill_color(*PAIN_BG)
    pdf.rect(sq_x, inner_y + half_h, sq_w, half_h, "F")

    # ── Square border + divider ───────────────────────────────────
    pdf.set_draw_color(*SQ_BORDER)
    pdf.set_line_width(0.8)
    pdf.rect(sq_x, inner_y, sq_w, sq_h)
    pdf.set_line_width(0.4)
    pdf.line(sq_x, inner_y + half_h, sq_x + sq_w, inner_y + half_h)

    # ── Gain Creators label + bullets ─────────────────────────────
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*DEEP_BLUE)
    pdf.set_xy(sq_x + 3, inner_y + 2)
    pdf.cell(sq_w - 6, 5, "Gain Creators")
    gy = inner_y + 8
    for g in gains[:2]:
        gy = _bullet_line(pdf, sq_x + 4, gy, sq_w - 8, g, DEEP_BLUE)
        gy += 1.5

    # ── Pain Relievers label + bullets ────────────────────────────
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*ACCENT)
    pdf.set_xy(sq_x + 3, inner_y + half_h + 2)
    pdf.cell(sq_w - 6, 5, "Pain Relievers")
    py = inner_y + half_h + 8
    for p in pains[:2]:
        py = _bullet_line(pdf, sq_x + 4, py, sq_w - 8, p, ACCENT)
        py += 1.5

    # ── Arrow ─────────────────────────────────────────────────────
    if arrow_x2 > arrow_x1 + 3:
        pdf.set_draw_color(*MID_GREY)
        pdf.set_line_width(0.5)
        pdf.line(arrow_x1, arrow_my, arrow_x2, arrow_my)
        ah = 1.8
        pdf.line(arrow_x2, arrow_my, arrow_x2 - ah, arrow_my - ah)
        pdf.line(arrow_x2, arrow_my, arrow_x2 - ah, arrow_my + ah)

    # ── Circle: top half fill (Gains — blue) ──────────────────────
    top_pts = _semicircle_polygon(cir_cx, cir_cy, cir_r, top=True)
    pdf.set_fill_color(*GAIN_BG)
    pdf.set_draw_color(*CIR_BORDER)
    pdf.set_line_width(0.0)
    pdf.polygon(top_pts, style="F")

    # ── Circle: bottom half fill (Pains — orange) ─────────────────
    bot_pts = _semicircle_polygon(cir_cx, cir_cy, cir_r, top=False)
    pdf.set_fill_color(*PAIN_BG)
    pdf.polygon(bot_pts, style="F")

    # ── Circle border (on top of fills) ───────────────────────────
    pdf.set_draw_color(*CIR_BORDER)
    pdf.set_line_width(0.8)
    pdf.ellipse(cir_bx, inner_y + (inner_h - cir_d) / 2, cir_d, cir_d, style="D")

    # ── Circle horizontal divider ─────────────────────────────────
    chord = cir_r * 0.90
    pdf.set_line_width(0.4)
    pdf.set_draw_color(*CIR_BORDER)
    pdf.line(cir_cx - chord, cir_cy, cir_cx + chord, cir_cy)

    # ── Circle labels ─────────────────────────────────────────────
    inner_cir_w = cir_r * 1.5

    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*DEEP_BLUE)
    pdf.set_xy(cir_cx - inner_cir_w, cir_cy - cir_r + 2)
    pdf.cell(inner_cir_w * 2, 4.5, "Gains", align="C")

    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*ACCENT)
    pdf.set_xy(cir_cx - inner_cir_w, cir_cy + 2)
    pdf.cell(inner_cir_w * 2, 4.5, "Pains", align="C")

    # ── Circle: job/gain items (top) ──────────────────────────────
    jy = cir_cy - cir_r + 8
    pdf.set_font("Helvetica", "", 5.8)
    pdf.set_text_color(*DARK_TEXT)
    for job in jobs[:2]:
        label = _clip_text(job, 28)
        pdf.set_xy(cir_cx - inner_cir_w, jy)
        pdf.cell(inner_cir_w * 2, 3.5, label, align="C")
        jy += 4

    # ── Circle: pain items (bottom) ───────────────────────────────
    pny = cir_cy + 8
    for pain in pains[:2]:
        label = _clip_text(pain, 26)
        pdf.set_xy(cir_cx - inner_cir_w, pny)
        pdf.cell(inner_cir_w * 2, 3.5, label, align="C")
        pny += 4

    # ── Customer Jobs title above circle ─────────────────────────
    title_y = inner_y + (inner_h - cir_d) / 2 - 5
    if title_y > inner_y:
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(*NAVY)
        pdf.set_xy(cir_bx, title_y)
        pdf.cell(cir_d, 4.5, "Customer Jobs", align="C")

    return y + h + 2
