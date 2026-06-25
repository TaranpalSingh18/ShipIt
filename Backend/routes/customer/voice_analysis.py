import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, TYPE_CHECKING

from dotenv import load_dotenv
from langchain_apify import ApifyActorsTool
from langchain_groq import ChatGroq
from tavily import TavilyClient

from schemas.teardown import CustomerVoiceAnalysis

if TYPE_CHECKING:
    from timing import PipelineTimer

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")
apify_api_key = os.getenv("APIFY_API_KEY")

MAX_WORKERS = min(8, (os.cpu_count() or 4) + 2)
APIFY_DEEP_LIMIT = 3
VOICE_COMPETITOR_LIMIT = int(os.getenv("VOICE_COMPETITOR_LIMIT", "3"))
VOICE_USE_APIFY = os.getenv("VOICE_USE_APIFY", "false").lower() in ("1", "true", "yes")
TAVILY_VOICE_MAX_RESULTS = int(os.getenv("TAVILY_VOICE_MAX_RESULTS", "3"))

VOICE_SYNTHESIS_PROMPT = """
You are a senior product researcher analyzing customer voice and market gaps.

Use ONLY the research evidence below. Do not invent reviews, complaints, or adoption data.
If evidence is thin for a competitor, set satisfaction_summary to "unknown" and keep complaints empty.

Product Context:
{product_context}

Competitors:
{competitors}

Research Evidence (per competitor):
{evidence}

Produce a CustomerVoiceAnalysis that:
1. current_solutions: what most customers use today (from evidence + product context)
2. competitor_sentiment: per competitor — what_users_use, satisfaction_summary (high/mixed/low/unknown), common_complaints
3. market_gaps: unmet needs with evidence from complaints; product_opportunity tied to the founder's idea
4. recommended_features: features that directly close the identified gaps

Only state dissatisfaction when evidence supports it.
"""


def minify_markdown(md_text: str, max_lines_per_site: int = 25) -> str:
    if not md_text:
        return ""

    md_text = re.sub(r"!\[.*?\]\(.*?\)", "", md_text)
    md_text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", md_text)
    md_text = re.sub(r"<[^>]+>", "", md_text)

    lines = md_text.split("\n")
    clean_lines = []
    for line in lines:
        line = line.strip()
        if len(line) > 40:
            clean_lines.append(line)

    clean_lines = clean_lines[:max_lines_per_site]
    return " ".join(clean_lines)


def _run_in_parallel(fn, items: list) -> list:
    if not items:
        return []

    worker_count = min(len(items), MAX_WORKERS)
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        return list(pool.map(fn, items))


def _tavily_competitor_search_uncached(competitor_name: str) -> dict[str, Any]:
    if not tavily_api_key:
        return {}

    client = TavilyClient(api_key=tavily_api_key)
    query = f"{competitor_name} user reviews complaints problems reddit"
    try:
        return client.search(query=query, max_results=TAVILY_VOICE_MAX_RESULTS)
    except Exception as e:
        print(f"Tavily voice search failed for {competitor_name}:", repr(e))
        return {}


@lru_cache(maxsize=128)
def _tavily_competitor_search_cached(competitor_name: str) -> str:
    started = time.perf_counter()
    result = _tavily_competitor_search_uncached(competitor_name)
    elapsed = time.perf_counter() - started
    print(f"[VOICE] Tavily fetch '{competitor_name}' ({elapsed:.2f}s)")
    return json.dumps(result, sort_keys=True, default=str)


def _tavily_competitor_search(competitor_name: str) -> dict[str, Any]:
    cache_info_before = _tavily_competitor_search_cached.cache_info()
    payload = _tavily_competitor_search_cached(competitor_name)
    cache_info_after = _tavily_competitor_search_cached.cache_info()
    if cache_info_after.hits > cache_info_before.hits:
        print(f"[VOICE] Tavily cache HIT for '{competitor_name}'")
    if not payload or payload == "{}":
        return {}
    return json.loads(payload)


def _apify_deep_scrape(competitor_name: str, product_context: str) -> str:
    if not apify_api_key or not VOICE_USE_APIFY:
        return ""

    context_snippet = product_context[:200].replace("\n", " ")
    query = f"{competitor_name} user reviews complaints alternatives {context_snippet}"

    started = time.perf_counter()
    try:
        browser = ApifyActorsTool(
            "apify/rag-web-browser",
            apify_api_token=apify_api_key,
        )
        raw_data = browser.invoke({"run_input": {"query": query}})
    except Exception as e:
        print(f"Apify deep scrape failed for {competitor_name}:", repr(e))
        return ""
    finally:
        print(f"[VOICE] Apify scrape '{competitor_name}' ({time.perf_counter() - started:.2f}s)")

    markdown_sources: list[str] = []
    if isinstance(raw_data, list):
        raw_markdowns = [
            item["markdown"]
            for item in raw_data
            if isinstance(item, dict) and item.get("markdown")
        ]
        if raw_markdowns:
            markdown_sources = _run_in_parallel(minify_markdown, raw_markdowns)

    return "\n\n---\n\n".join(markdown_sources)[:8000]


def _research_competitor(args: tuple[str, bool, str]) -> tuple[str, str]:
    competitor_name, use_apify, product_context = args
    started = time.perf_counter()
    parts: list[str] = []

    tavily_results = _tavily_competitor_search(competitor_name)
    if tavily_results:
        parts.append(f"TAVILY:\n{json.dumps(tavily_results, indent=2)}")

    if use_apify:
        apify_text = _apify_deep_scrape(competitor_name, product_context)
        if apify_text:
            parts.append(f"APIFY:\n{apify_text}")

    elapsed = time.perf_counter() - started
    print(f"[VOICE] Research done '{competitor_name}' total={elapsed:.2f}s apify={use_apify}")
    return competitor_name, "\n\n".join(parts) if parts else "No research evidence found."


def _empty_customer_voice() -> dict[str, Any]:
    return CustomerVoiceAnalysis().model_dump()


def _cap_competitors(competitors: list[str]) -> list[str]:
    if len(competitors) <= VOICE_COMPETITOR_LIMIT:
        return competitors

    print(
        f"[VOICE] Capping competitor research from {len(competitors)} "
        f"to {VOICE_COMPETITOR_LIMIT} (set VOICE_COMPETITOR_LIMIT to change)"
    )
    return competitors[:VOICE_COMPETITOR_LIMIT]


def generate_customer_voice(
    product_context: str,
    market_analysis: list[dict[str, str]],
    timer: "PipelineTimer | None" = None,
) -> dict[str, Any]:
    if not product_context or not market_analysis:
        return _empty_customer_voice()

    competitors = _cap_competitors([
        str(item.get("comp_name", "")).strip()
        for item in market_analysis
        if isinstance(item, dict) and str(item.get("comp_name", "")).strip()
    ])
    if not competitors:
        return _empty_customer_voice()

    if VOICE_USE_APIFY:
        print(f"[VOICE] Apify deep scrape ENABLED for top {APIFY_DEEP_LIMIT} competitors")
    else:
        print("[VOICE] Apify disabled (fast mode). Set VOICE_USE_APIFY=true for deeper research.")

    research_args = [
        (
            name,
            VOICE_USE_APIFY and apify_api_key is not None and idx < APIFY_DEEP_LIMIT,
            product_context,
        )
        for idx, name in enumerate(competitors)
    ]

    if timer:
        timer.start_phase("phase4_voice_competitor_research")

    worker_count = min(len(research_args), MAX_WORKERS)
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        research_results = list(pool.map(_research_competitor, research_args))

    evidence_blocks = [
        f"=== {name} ===\n{evidence}"
        for name, evidence in research_results
    ]
    evidence_text = "\n\n".join(evidence_blocks)

    if not groq_api_key:
        print("GROQ_API_KEY is missing; skipping customer voice synthesis")
        return _empty_customer_voice()

    if timer:
        timer.start_phase("phase4_voice_llm_synthesis")

    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=groq_api_key,
            temperature=0,
        ).with_structured_output(CustomerVoiceAnalysis)

        prompt = VOICE_SYNTHESIS_PROMPT.format(
            product_context=product_context,
            competitors=json.dumps(competitors, indent=2),
            evidence=evidence_text,
        )
        result = llm.invoke(prompt)
        return result.model_dump()
    except Exception as e:
        print("Customer voice synthesis failed:", repr(e))
        return _empty_customer_voice()
