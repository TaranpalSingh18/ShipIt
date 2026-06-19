import json
import os

from langchain_groq import ChatGroq
from pydantic import ValidationError

from ..query.query import ProductQuestions
from schemas.teardown import ProductTeardown, CustomerVoiceAnalysis

from .normalizer import parse_teardown_llm_output
from .prompts import TEARDOWN_JSON_PROMPT


class TeardownBuilder:

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
        )

    def _invoke_and_parse(
        self,
        prompt: str,
        market_analysis: list[dict[str, str]],
    ):
        response = self.llm.invoke(prompt)
        content = getattr(response, "content", str(response))
        return parse_teardown_llm_output(content, market_analysis)

    def build(self, questions: ProductQuestions) -> ProductTeardown:
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

        try:
            llm_output = self._invoke_and_parse(prompt, market_analysis)
        except (ValidationError, ValueError, json.JSONDecodeError) as first_error:
            print("Teardown parse failed, retrying once:", repr(first_error))
            retry_prompt = (
                prompt
                + "\n\nIMPORTANT: Return ONLY one valid JSON object. "
                "List fields MUST be JSON arrays of strings. "
                'competitors MUST be [{"name": "...", "why_competes": "..."}]. '
                "Do NOT duplicate keys. Do NOT add extra keys like type."
            )
            llm_output = self._invoke_and_parse(retry_prompt, market_analysis)

        customer_voice = (
            CustomerVoiceAnalysis(**customer_voice_data)
            if customer_voice_data
            else CustomerVoiceAnalysis()
        )

        return ProductTeardown(**llm_output.model_dump(), customer_voice=customer_voice)
