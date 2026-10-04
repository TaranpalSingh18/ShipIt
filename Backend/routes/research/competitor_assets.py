"""Logos and homepage screenshots for competitors, as data URIs.

Images are embedded in the report JSON so the PDF and the web report need no
further network access. Logos are cached on disk by domain.
"""

import asyncio
import base64
import io
import re
from pathlib import Path

import httpx
from PIL import Image

LOGO_CACHE = Path(__file__).resolve().parents[2] / "assets" / "logo_cache"
LOGO_URL = "https://www.google.com/s2/favicons?domain={domain}&sz=128"
SHOT_TIMEOUT_MS = 12000
SHOT_SIZE = (1280, 800)
THUMB_WIDTH = 720
# Pages that are not the real product: bot walls, parked domains, errors.
BAD_PAGE_MARKERS = (
    "access denied", "just a moment", "attention required", "are you a robot", "verify you are human",
    "forbidden", "for sale", "buy this domain", "parked", "page not found",
    "404 not found", "site can’t be reached", "cloudflare", "captcha",
)


def clean_domain(raw: str) -> str:
    raw = (raw or "").strip().lower()
    raw = re.sub(r"^https?://", "", raw).split("/")[0]
    raw = raw[4:] if raw.startswith("www.") else raw
    return raw if re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", raw) else ""


def _data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def fetch_logo(domain: str) -> str:
    domain = clean_domain(domain)
    if not domain:
        return ""
    LOGO_CACHE.mkdir(parents=True, exist_ok=True)
    cached = LOGO_CACHE / f"{domain}.png"
    if cached.is_file() and cached.stat().st_size > 0:
        return _data_uri(cached.read_bytes(), "image/png")

    try:
        response = httpx.get(LOGO_URL.format(domain=domain), timeout=6, follow_redirects=True)
    except Exception as exc:
        print(f"[ASSETS] logo fetch failed for {domain}:", repr(exc))
        return ""
    # Google answers 404 with a generic globe when it has no icon.
    if response.status_code != 200 or not response.content:
        return ""
    try:
        image = Image.open(io.BytesIO(response.content))
        if image.width < 32:
            return ""
        buffer = io.BytesIO()
        image.convert("RGBA").save(buffer, format="PNG")
    except Exception:
        return ""
    cached.write_bytes(buffer.getvalue())
    return _data_uri(buffer.getvalue(), "image/png")


async def _screenshot_one(browser, domain: str) -> str:
    page = await browser.new_page(viewport={"width": SHOT_SIZE[0], "height": SHOT_SIZE[1]})
    try:
        response = await page.goto(f"https://{domain}", wait_until="domcontentloaded", timeout=SHOT_TIMEOUT_MS)
        await page.wait_for_timeout(1800)
        if response is not None and response.status >= 400:
            print(f"[ASSETS] screenshot skipped for {domain}: HTTP {response.status}")
            return ""
        title = (await page.title()).lower()
        text = (await page.evaluate("document.body ? document.body.innerText.slice(0, 4000) : ''")).lower()
        if any(marker in title or marker in text[:600] for marker in BAD_PAGE_MARKERS) or len(text.strip()) < 60:
            print(f"[ASSETS] screenshot skipped for {domain}: blocked or parked page ({title[:60]!r})")
            return ""
        raw = await page.screenshot(type="png")
    except Exception as exc:
        print(f"[ASSETS] screenshot failed for {domain}:", repr(exc)[:160])
        return ""
    finally:
        await page.close()

    image = Image.open(io.BytesIO(raw)).convert("RGB")
    height = round(image.height * THUMB_WIDTH / image.width)
    image = image.resize((THUMB_WIDTH, height), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=72, optimize=True)
    return _data_uri(buffer.getvalue(), "image/jpeg")


async def _screenshots(domains: list[str]) -> list[str]:
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            semaphore = asyncio.Semaphore(4)

            async def guarded(domain: str) -> str:
                if not domain:
                    return ""
                async with semaphore:
                    return await _screenshot_one(browser, domain)

            return await asyncio.gather(*(guarded(domain) for domain in domains))
        finally:
            await browser.close()


def capture_screenshots(domains: list[str]) -> list[str]:
    """Blocking wrapper. Must be called from a thread with no running event loop."""
    domains = [clean_domain(domain) for domain in domains]
    if not any(domains):
        return ["" for _ in domains]
    try:
        return asyncio.run(_screenshots(domains))
    except Exception as exc:
        print("[ASSETS] screenshots skipped:", repr(exc))
        return ["" for _ in domains]
