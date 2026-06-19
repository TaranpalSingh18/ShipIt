import json
import re
from typing import Any

from pydantic import ValidationError

from schemas.teardown import ProductTeardownLLMOutput

LIST_FIELDS = (
    "target_users",
    "pain_points",
    "core_features",
    "user_journey",
    "moats",
    "opportunities",
    "risks",
)

STRING_FIELDS = (
    "product_name",
    "one_liner",
    "executive_summary",
    "market_positioning",
    "business_model",
    "verdict",
)

VALID_KEYS = set(ProductTeardownLLMOutput.model_fields.keys())


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()
    if text.startswith("```"):
        text = text.replace("```", "", 1).strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def parse_llm_json(content: str) -> dict[str, Any]:
    cleaned = strip_code_fences(content)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    return json.loads(cleaned[start : end + 1])


def _ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if "\n" in text:
            parts = [
                part.strip().lstrip("-•* ").strip()
                for part in re.split(r"[\n\r]+", text)
                if part.strip()
            ]
            if len(parts) > 1:
                return parts
        if ";" in text:
            parts = [part.strip() for part in text.split(";") if part.strip()]
            if len(parts) > 1:
                return parts
        return [text]
    return [str(value).strip()]


def _competitors_from_market(market_analysis: list[dict[str, str]]) -> list[dict[str, str]]:
    competitors: list[dict[str, str]] = []
    for item in market_analysis:
        if not isinstance(item, dict):
            continue
        name = str(item.get("comp_name", "")).strip()
        why = str(item.get("competitor_because", "")).strip()
        if name:
            competitors.append(
                {
                    "name": name,
                    "why_competes": why or "Competes in the same market segment.",
                }
            )
    return competitors


def _ensure_competitors(
    value: Any,
    market_analysis: list[dict[str, str]],
) -> list[dict[str, str]]:
    competitors: list[dict[str, str]] = []

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("comp_name") or "").strip()
                why = str(
                    item.get("why_competes") or item.get("competitor_because") or ""
                ).strip()
                if name:
                    competitors.append(
                        {
                            "name": name,
                            "why_competes": why or "Competes in the same market segment.",
                        }
                    )
            elif isinstance(item, str) and item.strip():
                competitors.append(
                    {
                        "name": item.strip(),
                        "why_competes": "Competes in the same market segment.",
                    }
                )

    if competitors:
        return competitors

    return _competitors_from_market(market_analysis)


def normalize_teardown_dict(
    raw: dict[str, Any],
    market_analysis: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    market_analysis = market_analysis or []
    normalized: dict[str, Any] = {}

    for key in VALID_KEYS:
        value = raw.get(key)
        if key in LIST_FIELDS:
            normalized[key] = _ensure_list(value)
        elif key == "competitors":
            normalized[key] = _ensure_competitors(value, market_analysis)
        elif key in STRING_FIELDS:
            normalized[key] = str(value or "").strip()

    if not normalized.get("product_name"):
        normalized["product_name"] = "Product Teardown"
    if not normalized.get("one_liner"):
        normalized["one_liner"] = "A product opportunity under analysis."
    if not normalized.get("executive_summary"):
        normalized["executive_summary"] = "Executive summary unavailable from model output."
    if not normalized.get("market_positioning"):
        normalized["market_positioning"] = "Market positioning requires further research."
    if not normalized.get("business_model"):
        normalized["business_model"] = "Business model requires further definition."
    if not normalized.get("verdict"):
        normalized["verdict"] = normalized.get("executive_summary", "Verdict pending.")

    return normalized


def parse_teardown_llm_output(
    content: str,
    market_analysis: list[dict[str, str]] | None = None,
) -> ProductTeardownLLMOutput:
    raw = parse_llm_json(content)
    normalized = normalize_teardown_dict(raw, market_analysis)
    return ProductTeardownLLMOutput(**normalized)
