"""Render the investor memo from a fixture JSON, without any LLM calls.

    python scripts/render_sample_report.py [fixture.json] [--png]

Writes output/sample_report.pdf (and output/sample_report.html). With --png,
also screenshots every page to output/sample_pages/ for visual review.
"""

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from routes.report.render import FIT_SCRIPT, OUTPUT_DIR, build_html, render_pdf  # noqa: E402
from schemas.report import InvestorReport  # noqa: E402


async def _pngs(html: str, folder: Path) -> None:
    from playwright.async_api import async_playwright

    folder.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=1.6)
        await page.set_content(html, wait_until="load")
        await page.evaluate("document.fonts.ready")
        print(await page.evaluate(FIT_SCRIPT))
        for index, section in enumerate(await page.query_selector_all(".page"), start=1):
            await section.screenshot(path=str(folder / f"page_{index:02d}.png"))
        await browser.close()


def main() -> None:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    fixture = Path(args[0]) if args else BACKEND / "scripts" / "fixtures" / "sample_report.json"
    report = InvestorReport.model_validate_json(fixture.read_text(encoding="utf-8"))
    html = build_html(report)
    (OUTPUT_DIR / "sample_report.html").write_text(html, encoding="utf-8")
    print("PDF:", render_pdf(report, "sample_report.pdf"))
    if "--png" in sys.argv:
        asyncio.run(_pngs(html, OUTPUT_DIR / "sample_pages"))


if __name__ == "__main__":
    main()
