"""Turn an InvestorReport into print-ready HTML, then into a PDF with Chromium."""

import asyncio
import base64
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from routes.report import charts
from schemas.report import InvestorReport

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE.parents[1] / "assets" / "fonts"
OUTPUT_DIR = HERE.parents[1] / "output"

FONTS = [
    ("Inter", "inter-latin-wght-normal.woff2", "normal", "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
    ("Inter", "inter-latin-ext-wght-normal.woff2", "normal", "U+0100-02AF, U+0304, U+0308, U+0329, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF"),
    ("Fraunces", "fraunces-latin-wght-normal.woff2", "normal", ""),
    ("Fraunces", "fraunces-latin-wght-italic.woff2", "italic", ""),
    ("JetBrains Mono", "jetbrains-mono-latin-wght-normal.woff2", "normal", ""),
]

# Shrinks any page whose content overflows, so nothing is clipped silently.
FIT_SCRIPT = """
() => {
  const report = [];
  document.querySelectorAll('.page').forEach((page) => {
    const body = page.querySelector('.page-body');
    if (!body) return;
    let zoom = 1;
    while (body.scrollHeight > body.clientHeight + 1 && zoom > 0.74) {
      zoom -= 0.02;
      body.style.zoom = zoom.toFixed(2);
    }
    // Sparse pages grow a little so they don't end in a large blank band.
    if (zoom === 1) {
      while (zoom < 1.12) {
        body.style.zoom = (zoom + 0.02).toFixed(2);
        if (body.scrollHeight > body.clientHeight + 1) { body.style.zoom = zoom.toFixed(2); break; }
        zoom += 0.02;
      }
    }
    report.push({ page: page.dataset.page, zoom: Number(zoom.toFixed(2)),
                  overflow: body.scrollHeight > body.clientHeight + 1 });
  });
  return report;
}
"""


@lru_cache(maxsize=1)
def _font_css() -> str:
    rules = []
    for family, filename, style, unicode_range in FONTS:
        path = FONT_DIR / filename
        if not path.is_file():
            continue
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        range_rule = f"unicode-range:{unicode_range};" if unicode_range else ""
        rules.append(
            f"@font-face{{font-family:'{family}';font-style:{style};font-weight:100 900;"
            f"font-display:block;src:url(data:font/woff2;base64,{data}) format('woff2');{range_rule}}}"
        )
    return "\n".join(rules)


def _initials(name: str) -> str:
    words = [word for word in name.replace("-", " ").split() if word]
    if not words:
        return "?"
    return (words[0][0] + (words[1][0] if len(words) > 1 else words[0][1:2])).upper()


@lru_cache(maxsize=1)
def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(HERE / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def cite(ids: list[int] | None) -> Markup:
        ids = [sid for sid in (ids or []) if isinstance(sid, int)]
        if not ids:
            return Markup("")
        return Markup('<sup class="cite">[' + ", ".join(str(sid) for sid in ids[:4]) + "]</sup>")

    env.filters["cite"] = cite
    env.filters["initials"] = _initials
    env.filters["svg"] = lambda value: Markup(value)
    return env


def _cited_ids(report: InvestorReport) -> set[int]:
    ids: set[int] = set()
    market = report.market
    for figure in (market.tam, market.sam, market.som, market.cagr):
        ids.update(figure.source_ids)
    for trend in market.trends:
        ids.update(trend.source_ids)
    for comp in report.competition.competitors:
        ids.update(comp.source_ids)
    return ids


def build_html(report: InvestorReport) -> str:
    comp = report.competition
    strategy = report.strategy
    pains = {pain.id: pain for pain in report.narrative.pains}
    gains = {gain.id: gain for gain in report.narrative.value_prop.gains}
    cited = _cited_ids(report)
    try:
        generated = datetime.fromisoformat(report.meta.generated_at).strftime("%d %B %Y")
    except ValueError:
        generated = datetime.now().strftime("%d %B %Y")

    risk_cells: dict[tuple[int, int], list[int]] = {}
    for number, risk in enumerate(strategy.risks, start=1):
        risk_cells.setdefault((risk.likelihood, risk.impact), []).append(number)

    sentiment = {item.name.lower(): item for item in report.customer_voice.competitor_sentiment}
    max_mentions = max([theme.mentions for theme in comp.complaint_themes] or [1])

    context = {
        "r": report,
        "n": report.narrative,
        "m": report.market,
        "c": comp,
        "s": strategy,
        "v": report.customer_voice,
        "meta": report.meta,
        "generated": generated,
        "font_css": _font_css(),
        "pains": pains,
        "gains": gains,
        "risk_cells": risk_cells,
        "sentiment": sentiment,
        "max_mentions": max_mentions,
        "cited": cited,
        "ring": charts.score_ring(report.meta.readiness),
        "ring_small": charts.score_ring(report.meta.readiness, size=112, stroke=10),
        "tam_svg": charts.tam_circles(report.market.tam, report.market.sam, report.market.som),
        "positioning_svg": charts.positioning_map(comp.positioning) if comp.positioning.points else "",
        "radar_svg": charts.radar(strategy.scorecard),
    }
    return _env().get_template("report.html.j2").render(**context)


async def _print(html: str, path: Path) -> list[dict]:
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page()
            await page.set_content(html, wait_until="load")
            await page.evaluate("document.fonts.ready")
            fit = await page.evaluate(FIT_SCRIPT)
            await page.pdf(
                path=str(path),
                width="210mm",
                height="297mm",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                prefer_css_page_size=True,
            )
            return fit
        finally:
            await browser.close()


def render_pdf(report: InvestorReport, filename: str) -> Path:
    """Blocking. Call from a worker thread (no running event loop)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    fit = asyncio.run(_print(build_html(report), path))
    squeezed = [item for item in fit if item["zoom"] < 1 or item["overflow"]]
    if squeezed:
        print("[REPORT] pages scaled to fit:", squeezed)
    return path
