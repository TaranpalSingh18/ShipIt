import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from dotenv import load_dotenv
from langchain_apify import ApifyActorsTool
from langchain_groq import ChatGroq
from tavily import TavilyClient

from schemas.teardown import CustomerVoiceAnalysis

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")
apify_api_key = os.getenv("APIFY_API_KEY")

MAX_WORKERS = min(8, (os.cpu_count() or 4) + 2)
APIFY_DEEP_LIMIT = 3

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


def _tavily_competitor_search(competitor_name: str) -> dict[str, Any]:
    if not tavily_api_key:
        return {}

    client = TavilyClient(api_key=tavily_api_key)
    query = f"{competitor_name} user reviews complaints problems reddit"
    try:
        return client.search(query=query, max_results=5)
    except Exception as e:
        print(f"Tavily voice search failed for {competitor_name}:", repr(e))
        return {}


def _apify_deep_scrape(competitor_name: str, product_context: str) -> str:
    if not apify_api_key:
        return ""

    context_snippet = product_context[:200].replace("\n", " ")
    query = f"{competitor_name} user reviews complaints alternatives {context_snippet}"

    try:
        browser = ApifyActorsTool(
            "apify/rag-web-browser",
            apify_api_token=apify_api_key,
        )
        raw_data = browser.invoke({"run_input": {"query": query}})
    except Exception as e:
        print(f"Apify deep scrape failed for {competitor_name}:", repr(e))
        return ""

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
    parts: list[str] = []

    tavily_results = _tavily_competitor_search(competitor_name)
    if tavily_results:
        parts.append(f"TAVILY:\n{json.dumps(tavily_results, indent=2)}")

    if use_apify:
        apify_text = _apify_deep_scrape(competitor_name, product_context)
        if apify_text:
            parts.append(f"APIFY:\n{apify_text}")

    return competitor_name, "\n\n".join(parts) if parts else "No research evidence found."


def _empty_customer_voice() -> dict[str, Any]:
    return CustomerVoiceAnalysis().model_dump()


def generate_customer_voice(
    product_context: str,
    market_analysis: list[dict[str, str]],
) -> dict[str, Any]:
    if not product_context or not market_analysis:
        return _empty_customer_voice()

    competitors = [
        str(item.get("comp_name", "")).strip()
        for item in market_analysis
        if isinstance(item, dict) and str(item.get("comp_name", "")).strip()
    ]
    if not competitors:
        return _empty_customer_voice()

    research_args = [
        (name, apify_api_key is not None and idx < APIFY_DEEP_LIMIT, product_context)
        for idx, name in enumerate(competitors)
    ]

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
