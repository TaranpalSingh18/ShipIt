import json
import os

from langchain_groq import ChatGroq

from ..query.query import ProductQuestions
from schemas.teardown import ProductTeardown

from .prompts import TEARDOWN_PROMPT


class TeardownBuilder:

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
        ).with_structured_output(ProductTeardown)

    def build(self, questions: ProductQuestions) -> ProductTeardown:
        prompt = TEARDOWN_PROMPT.format(
            user_query=questions["user_query"],
            fully_answered=questions["fully_answered"],
            follow_up_questions=json.dumps(questions["follow_up_questions"], indent=2),
            question_mapping=json.dumps(questions["question_mapping"], indent=2),
            product_context=questions["product_context"],
            market_search_query=questions["market_search_query"],
            market_analysis=json.dumps(questions["market_analysis"], indent=2),
        )

        return self.llm.invoke(prompt)