import json
import os
from typing import TYPE_CHECKING

from langchain_groq import ChatGroq
from pydantic import ValidationError

from ..query.query import ProductQuestions
from schemas.teardown import (
    ProductTeardown,
    CustomerVoiceAnalysis,
    ProductTeardownLLMOutput,
)

from .normalizer import parse_teardown_llm_output
from .prompts import TEARDOWN_JSON_PROMPT

if TYPE_CHECKING:
    from timing import PipelineTimer


class TeardownBuilder:

    def __init__(self):
        import os_trust

        os_trust.enable()
        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
        )
        # Structured output LLM to reduce JSON parsing failures.
        self.structured_llm = self.llm.with_structured_output(ProductTeardownLLMOutput)

    def _invoke_and_parse(
        self,
        prompt: str,
        market_analysis: list[dict[str, str]],
    ):
        response = self.llm.invoke(prompt)
        content = getattr(response, "content", str(response))
        return parse_teardown_llm_output(content, market_analysis)

    def _invoke_structured(self, prompt: str) -> ProductTeardownLLMOutput:
        """
        Prefer structured output to avoid JSON decoding errors.
        """
        return self.structured_llm.invoke(prompt)

    def build(
        self,
        questions: ProductQuestions,
        timer: "PipelineTimer | None" = None,
    ) -> ProductTeardown:
        customer_voice_data = questions.get("customer_voice") or {}
        market_analysis = questions.get("market_analysis") or []

        prompt = TEARDOWN_JSON_PROMPT.format(
            user_query=questions["user_query"],
            fully_answered=questions["fully_answered"],
            follow_up_questions=json.dumps(questions["follow_up_questions"], indent=2),
            question_mapping=json.dumps(questions["question_mapping"], indent=2),
            product_context=questions["product_context"],
            market_search_query=questions["market_search_query"],
            market_analysis=json.dumps(market_analysis, indent=2),
            customer_voice=json.dumps(customer_voice_data, indent=2),
        )

        # Phase 5 timing block
        if timer:
            timer.start_phase("phase5_teardown_llm")

        # First attempt: structured output (strongest safety)
        try:
            structured = self._invoke_structured(prompt)
            normalized = structured.model_dump()
            llm_output = ProductTeardownLLMOutput(**normalized)
        except Exception as structured_error:
            print("Teardown structured parse failed, falling back:", repr(structured_error))
            # Fallback to legacy parse with retry + stricter instructions
            try:
                llm_output = self._invoke_and_parse(prompt, market_analysis)
            except (ValidationError, ValueError, json.JSONDecodeError) as first_error:
                print("Teardown parse failed, retrying once:", repr(first_error))
                if timer:
                    timer.start_phase("phase5_teardown_llm_retry")
                retry_prompt = (
                    prompt
                    + "\n\nIMPORTANT: Return ONLY one valid JSON object. "
                    "Double-quoted keys/strings. No trailing commas. "
                    "List fields MUST be JSON arrays. "
                    'competitors MUST be [{"name": "...", "why_competes": "..."}]. '
                    "Do NOT duplicate keys. Do NOT add extra keys."
                )
                llm_output = self._invoke_and_parse(retry_prompt, market_analysis)

        customer_voice = (
            CustomerVoiceAnalysis(**customer_voice_data)
            if customer_voice_data
            else CustomerVoiceAnalysis()
        )

        return ProductTeardown(**llm_output.model_dump(), customer_voice=customer_voice)
