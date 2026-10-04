"""Web research for the investor report.

Every search result is kept in a numbered `SourceRegistry`, so the LLM can cite
`source_ids` and the generator can drop any number whose source does not exist.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

tavily_api_key = os.getenv("TAVILY_API_KEY")
SNIPPET_CHARS = 450


def domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


class SourceRegistry:
    """Numbered, de-duplicated list of web sources."""

    def __init__(self) -> None:
        self._by_url: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add(self, url: str, title: str, content: str) -> int | None:
        url = (url or "").strip()
        if not url.startswith("http"):
            return None
        with self._lock:
            if url not in self._by_url:
                self._by_url[url] = {
                    "id": len(self._by_url) + 1,
                    "title": (title or domain_of(url)).strip()[:160],
                    "url": url,
                    "domain": domain_of(url),
                    "content": " ".join((content or "").split())[:SNIPPET_CHARS],
                }
            return self._by_url[url]["id"]

    def ids(self) -> set[int]:
        return {item["id"] for item in self._by_url.values()}

    def get(self, source_id: int) -> dict[str, Any] | None:
        for item in self._by_url.values():
            if item["id"] == source_id:
                return item
        return None

    def as_prompt(self, ids: list[int] | None = None) -> str:
        """Render sources as a numbered block for an LLM prompt."""
        items = sorted(self._by_url.values(), key=lambda item: item["id"])
        if ids is not None:
            wanted = set(ids)
            items = [item for item in items if item["id"] in wanted]
        if not items:
            return "(no sources found)"
        return "\n\n".join(
            f"[{item['id']}] {item['title']} ({item['domain']})\n{item['content']}"
            for item in items
        )

    def public(self) -> list[dict[str, Any]]:
        return [
            {key: item[key] for key in ("id", "title", "url", "domain")}
            for item in sorted(self._by_url.values(), key=lambda item: item["id"])
        ]


def tavily_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    if not tavily_api_key or not query.strip():
        return []
    try:
        response = TavilyClient(api_key=tavily_api_key).search(
            query=query[:380],
            max_results=max_results,
        )
    except Exception as exc:
        print(f"[RESEARCH] Tavily failed for '{query}':", repr(exc))
        return []
    return [
        {
            "url": str(item.get("url", "")),
            "title": str(item.get("title", "")),
            "content": str(item.get("content", "")),
        }
        for item in response.get("results", [])
        if isinstance(item, dict)
    ]


def _register(registry: SourceRegistry, results: list[dict[str, str]]) -> list[int]:
    ids = []
    for result in results:
        source_id = registry.add(result["url"], result["title"], result["content"])
        if source_id is not None:
            ids.append(source_id)
    return ids


def research_market(registry: SourceRegistry, category: str, keywords: list[str]) -> list[int]:
    """Search for market size and growth. Returns the source ids found."""
    if not category and not keywords:
        return []
    queries = [f"{category} market size 2025 billion CAGR forecast"] if category else []
    queries += [f"{keyword} size 2025 USD billion CAGR" for keyword in keywords[:2]]
    queries.append(f"{category or keywords[0]} industry trends 2025")
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        batches = list(pool.map(lambda q: tavily_search(q, max_results=5), queries))
    ids: list[int] = []
    for batch in batches:
        ids.extend(_register(registry, batch))
    return list(dict.fromkeys(ids))


def _name_tokens(name: str) -> list[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in name)
    return [token for token in cleaned.split() if len(token) > 2] or [cleaned.replace(" ", "")]


def guess_domain(name: str, results: list[dict[str, str]]) -> str:
    """Pick the result whose domain contains the competitor's name."""
    tokens = _name_tokens(name)
    joined = "".join(tokens)
    for result in results:
        domain = domain_of(result["url"])
        root = domain.split(".")[0] if domain else ""
        if not root:
            continue
        if joined and (joined in domain.replace("-", "") or root in joined):
            return domain
        if any(token in root for token in tokens):
            return domain
    return ""


def research_competitor(registry: SourceRegistry, name: str) -> dict[str, Any]:
    """Pricing + company facts for one competitor."""
    queries = [
        f"{name} pricing plans",
        f"{name} company founded headquarters funding raised",
    ]
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        pricing, company = list(pool.map(lambda q: tavily_search(q, max_results=3), queries))
    ids = _register(registry, pricing) + _register(registry, company)
    return {
        "name": name,
        "domain": guess_domain(name, pricing + company),
        "source_ids": list(dict.fromkeys(ids)),
    }


def research_competitors(registry: SourceRegistry, names: list[str]) -> list[dict[str, Any]]:
    if not names:
        return []
    with ThreadPoolExecutor(max_workers=min(6, len(names))) as pool:
        return list(pool.map(lambda name: research_competitor(registry, name), names))
