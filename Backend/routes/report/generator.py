"""Build an InvestorReport from a fully answered project.

Flow (each step reports progress):
  1. research   - narrative LLM call  ||  competitor web research
  2. writing    - market research + market call || competition call || strategy call
  3. assets     - competitor logos and homepage screenshots
  4. assemble   - drop figures whose sources do not exist, compute scores
"""

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

from langchain_groq import ChatGroq
from pydantic import BaseModel

from routes.research.competitor_assets import capture_screenshots, clean_domain, fetch_logo
from routes.research.market_research import (
    SourceRegistry,
    research_competitors,
    research_market,
)
from routes.report import prompts
from schemas.report import (
    CompetitionSection,
    Figure,
    InvestorReport,
    MarketSection,
    NarrativeSection,
    ReportMeta,
    Score,
    StrategySection,
)
from schemas.teardown import CustomerVoiceAnalysis

Progress = Callable[[str, int, str], None]
T = TypeVar("T", bound=BaseModel)

MAX_COMPETITORS = int(os.getenv("REPORT_MAX_COMPETITORS", "5"))
SCORE_DIMENSIONS = ["Problem", "Market", "Differentiation", "Feasibility", "Evidence"]
NOT_FOUND = "Not found"

# Groq's on-demand tier allows ~8K tokens/minute per model, so each model gets a
# lock (one call at a time) and calls wait out 429s. Two models = two parallel lanes.
MODELS = {
    "large": os.getenv("REPORT_MODEL_LARGE", "openai/gpt-oss-120b"),
    "small": os.getenv("REPORT_MODEL_SMALL", "openai/gpt-oss-20b"),
}
MAX_PROMPT_CHARS = int(os.getenv("REPORT_MAX_PROMPT_CHARS", "17000"))
_llms: dict[str, ChatGroq] = {}
_locks = {tier: threading.Lock() for tier in MODELS}


def _get_llm(tier: str) -> ChatGroq:
    if tier not in _llms:
        import os_trust

        os_trust.enable()
        _llms[tier] = ChatGroq(
            model=MODELS[tier],
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
            max_tokens=int(os.getenv("REPORT_MAX_TOKENS", "5000")),
            reasoning_effort="low",
        )
    return _llms[tier]


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end != -1 else text


def _retry_after(exc: Exception) -> float | None:
    """Seconds to wait if this is a rate-limit error, else None."""
    text = repr(exc)
    if "429" not in text and "rate_limit" not in text.lower():
        return None
    match = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", text)
    if not match:
        return 20.0
    return min(90.0, float(match.group(1) or 0) * 60 + float(match.group(2)) + 1.5)


def _call(tier: str, fn, label: str):
    for attempt in range(6):
        with _locks[tier]:
            try:
                return fn(_get_llm(tier))
            except Exception as exc:
                wait = _retry_after(exc)
                if wait is None:
                    raise
        print(f"[REPORT] {label}: rate limited, waiting {wait:.0f}s (attempt {attempt + 1})")
        time.sleep(wait)
    raise RuntimeError(f"{label}: still rate limited after retries")


def _ask(model: type[T], prompt: str, label: str, tier: str = "large") -> T:
    """Structured output first; fall back to plain JSON with the schema attached."""
    if len(prompt) > MAX_PROMPT_CHARS:
        print(f"[REPORT] {label}: prompt is {len(prompt)} chars, above the {MAX_PROMPT_CHARS} budget")
    try:
        result = _call(tier, lambda llm: llm.with_structured_output(model).invoke(prompt), label)
        return result if isinstance(result, model) else model.model_validate(result)
    except Exception as exc:
        print(f"[REPORT] {label}: structured output failed, retrying as JSON:", repr(exc)[:300])

    schema = json.dumps(model.model_json_schema(), separators=(",", ":"))
    retry = (
        f"{prompt}\n\nReturn ONLY one JSON object (no prose, no code fences) "
        f"that matches this JSON schema:\n{schema}"
    )
    try:
        content = _call(tier, lambda llm: llm.invoke(retry).content, label)
        return model.model_validate_json(_strip_fences(str(content)))
    except Exception as exc:
        print(f"[REPORT] {label}: JSON fallback failed, using empty section:", repr(exc)[:300])
    return model()


def _clamp(value: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return low


def _context_block(state: dict[str, Any]) -> str:
    answers = {
        key: (value or {}).get("answer", "")
        for key, value in (state.get("question_mapping") or {}).items()
        if isinstance(value, dict)
    }
    return prompts.CONTEXT.format(
        idea=str(state.get("user_query", "")).split("\n\nAdditional context:")[0].strip(),
        answers=json.dumps(answers, ensure_ascii=False),
        product_context=str(state.get("product_context", ""))[:2500],
        competitors=json.dumps(state.get("market_analysis") or [], ensure_ascii=False),
        customer_voice=json.dumps(state.get("customer_voice") or {}, ensure_ascii=False)[:3500],
    )


# ---------- validation ----------

def _check_figure(figure: Figure, valid: set[int], allow_derived: bool) -> Figure:
    figure.source_ids = [sid for sid in figure.source_ids if sid in valid]
    figure.confidence = figure.confidence if figure.confidence in ("high", "medium", "low") else "low"
    derived = allow_derived and figure.method in ("top-down", "bottom-up")
    if not figure.source_ids and not derived:
        figure.value_usd = None
        figure.display = NOT_FOUND
        figure.confidence = "low"
        figure.note = "No source in the research supported a figure."
    if figure.value_usd is None and figure.display != NOT_FOUND:
        figure.display = figure.display or NOT_FOUND
    return figure


def _validate_market(market: MarketSection, valid: set[int]) -> MarketSection:
    market.tam = _check_figure(market.tam, valid, allow_derived=False)
    market.cagr = _check_figure(market.cagr, valid, allow_derived=False)
    tam_ok = market.tam.value_usd is not None
    market.sam = _check_figure(market.sam, valid, allow_derived=tam_ok)
    market.som = _check_figure(market.som, valid, allow_derived=tam_ok)
    for trend in market.trends:
        trend.source_ids = [sid for sid in trend.source_ids if sid in valid]
    return market


def _voice_digest(voice: dict[str, Any]) -> str:
    """Compact per-competitor sentiment for prompts that cannot take the full JSON."""
    lines = []
    for item in voice.get("competitor_sentiment") or []:
        complaints = "; ".join((item.get("common_complaints") or [])[:4])
        lines.append(
            f"- {item.get('name', '')}: satisfaction {item.get('satisfaction_summary', 'unknown')}"
            f" | complaints: {complaints or 'none found'}"
        )
    for gap in (voice.get("market_gaps") or [])[:4]:
        lines.append(f"- GAP: {gap.get('gap', '')} (evidence: {gap.get('evidence', '')})")
    return "\n".join(lines)[:3000] or "(no customer voice)"


def _validate_competition(
    competition: CompetitionSection,
    valid: set[int],
    research: list[dict[str, Any]],
    product_name: str,
) -> CompetitionSection:
    by_name = {item["name"].lower(): item for item in research}
    by_domain = {item["domain"]: item for item in research if item["domain"]}
    unnamed = [item["name"] for item in research]
    for comp in competition.competitors:
        if comp.name.lower() in by_name or (comp.name and comp.name in unnamed):
            unnamed = [name for name in unnamed if name.lower() != comp.name.lower()]
    for index, comp in enumerate(competition.competitors):
        # The smaller model sometimes leaves names blank; recover them from research.
        if not comp.name.strip():
            match = by_domain.get(clean_domain(comp.domain))
            comp.name = match["name"] if match else (unnamed.pop(0) if unnamed else f"Competitor {index + 1}")
        comp.source_ids = [sid for sid in comp.source_ids if sid in valid]
        if not comp.source_ids:
            comp.founded = comp.hq = comp.funding = comp.pricing = ""
        found = by_name.get(comp.name.lower(), {})
        comp.domain = clean_domain(found.get("domain") or comp.domain)
        comp.satisfaction = comp.satisfaction if comp.satisfaction in ("high", "mixed", "low") else "unknown"
        comp.satisfaction_score = _clamp(comp.satisfaction_score, 0, 100)
        if comp.satisfaction_score == 50 and comp.satisfaction != "unknown":
            comp.satisfaction_score = {"high": 80, "mixed": 52, "low": 25}[comp.satisfaction]
        comp.threat = comp.threat if comp.threat in ("high", "medium", "low") else "medium"

    width = len(competition.feature_matrix.capabilities)
    for row in competition.feature_matrix.rows:
        row.scores = [_clamp(score, 0, 2) for score in row.scores[:width]]
        row.scores += [0] * (width - len(row.scores))

    us = product_name.lower()
    has_us = False
    for point in competition.positioning.points:
        point.x = _clamp(point.x, 0, 100)
        point.y = _clamp(point.y, 0, 100)
        point.is_us = point.is_us or point.name.lower() == us
        has_us = has_us or point.is_us
    if not has_us and competition.positioning.points:
        competition.positioning.points[0].is_us = True

    for theme in competition.complaint_themes:
        theme.mentions = _clamp(theme.mentions, 1, 20)
    return competition


def _validate_strategy(strategy: StrategySection) -> StrategySection:
    for risk in strategy.risks:
        risk.likelihood = _clamp(risk.likelihood, 1, 3)
        risk.impact = _clamp(risk.impact, 1, 3)
    for moat in strategy.moats:
        moat.strength = _clamp(moat.strength, 1, 5)

    by_name = {score.dimension.lower(): score for score in strategy.scorecard}
    strategy.scorecard = [
        by_name.get(name.lower()) or Score(dimension=name, score=5, rationale="Not assessed.")
        for name in SCORE_DIMENSIONS
    ]
    for score in strategy.scorecard:
        score.score = _clamp(score.score, 0, 10)

    label = strategy.verdict.label.strip().lower()
    strategy.verdict.label = (
        "Strong" if label.startswith("strong")
        else "Promising" if label.startswith("promis")
        else "Needs validation"
    )
    return strategy


def _evidence_level(source_count: int, voice: CustomerVoiceAnalysis) -> str:
    complaints = sum(len(item.common_complaints) for item in voice.competitor_sentiment)
    if source_count >= 15 and complaints >= 6:
        return "high"
    if source_count >= 6 or complaints >= 3:
        return "medium"
    return "low"


# ---------- main ----------

def generate_report(state: dict[str, Any], progress: Progress | None = None) -> InvestorReport:
    def report_progress(step: str, pct: int, label: str) -> None:
        print(f"[REPORT] {pct:>3}% {label}")
        if progress:
            progress(step, pct, label)

    context = _context_block(state)
    registry = SourceRegistry()
    competitor_names = [
        str(item.get("comp_name", "")).strip()
        for item in (state.get("market_analysis") or [])
        if isinstance(item, dict) and str(item.get("comp_name", "")).strip()
    ][:MAX_COMPETITORS]

    # 1. narrative || competitor research
    report_progress("research", 8, "Researching competitors and framing the story")
    with ThreadPoolExecutor(max_workers=2) as pool:
        narrative_future = pool.submit(
            _ask, NarrativeSection, prompts.NARRATIVE.format(context=context), "narrative", "large"
        )
        research_future = pool.submit(research_competitors, registry, competitor_names)
        narrative = narrative_future.result()
        competitor_research = research_future.result()
    product_name = narrative.product_name or "The product"

    # 2. market || competition || strategy
    report_progress("writing", 30, "Sizing the market and writing the analysis")
    competitor_sources = "\n\n".join(
        f"=== {item['name']} (domain guess: {item['domain'] or 'unknown'}) ===\n"
        + registry.as_prompt(item["source_ids"])
        for item in competitor_research
    )[:6500] or "(no competitor research)"
    summary = json.dumps(
        {
            "product_name": product_name,
            "one_liner": narrative.one_liner,
            "category": narrative.category,
            "pains": [pain.title for pain in narrative.pains],
            "segments": [seg.name for seg in narrative.segments],
            "competitors": competitor_names,
        },
        indent=2,
    )

    def market_call() -> MarketSection:
        ids = research_market(registry, narrative.category, narrative.market_keywords)
        report_progress("writing", 45, "Market sources collected")
        prompt = prompts.MARKET.format(summary=summary, sources=registry.as_prompt(ids))
        market = _ask(MarketSection, prompt, "market", "small")
        if not market.tam.label and not market.trends:
            # The small model occasionally returns an empty shell; the large one is steadier.
            print("[REPORT] market: empty answer from the small model, retrying on the large one")
            market = _ask(MarketSection, prompt, "market-retry", "large")
        return market

    with ThreadPoolExecutor(max_workers=3) as pool:
        market_future = pool.submit(market_call)
        competition_future = pool.submit(
            _ask,
            CompetitionSection,
            prompts.COMPETITION.format(
                context=context,
                summary=summary,
                product_name=product_name,
                competitor_names=", ".join(competitor_names),
                voice=_voice_digest(state.get("customer_voice") or {}),
                sources=competitor_sources,
            ),
            "competition",
            "small",
        )
        strategy_future = pool.submit(
            _ask,
            StrategySection,
            prompts.STRATEGY.format(context=context, summary=summary),
            "strategy",
            "large",
        )
        market = market_future.result()
        competition = competition_future.result()
        strategy = strategy_future.result()

    valid = registry.ids()
    market = _validate_market(market, valid)
    competition = _validate_competition(competition, valid, competitor_research, product_name)
    strategy = _validate_strategy(strategy)

    # 3. logos and screenshots
    report_progress("assets", 75, "Capturing competitor logos and homepages")
    domains = [comp.domain for comp in competition.competitors]
    with ThreadPoolExecutor(max_workers=6) as pool:
        logos = list(pool.map(fetch_logo, domains))
    screenshots = capture_screenshots(domains)
    for comp, logo, shot in zip(competition.competitors, logos, screenshots):
        comp.logo, comp.screenshot = logo, shot

    # 4. assemble
    voice = CustomerVoiceAnalysis(**(state.get("customer_voice") or {}))
    pain_signals = sum(len(item.common_complaints) for item in voice.competitor_sentiment) + len(
        voice.market_gaps
    )
    scores = [score.score for score in strategy.scorecard]
    meta = ReportMeta(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        idea=str(state.get("user_query", "")).split("\n\nAdditional context:")[0].strip(),
        readiness=round(sum(scores) / len(scores) * 10) if scores else 0,
        competitors_analysed=len(competition.competitors),
        pain_signals=pain_signals,
        evidence=_evidence_level(len(valid), voice),
    )
    narrative.product_name = product_name
    return InvestorReport(
        meta=meta,
        narrative=narrative,
        market=market,
        competition=competition,
        strategy=strategy,
        customer_voice=voice,
        sources=registry.public(),
    )
