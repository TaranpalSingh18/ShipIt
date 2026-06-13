from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

from schemas.query_schema import QueryRequest
from ..query.query import ProductQuestions

from ..query.query import run_product_pipeline
from .builder import TeardownBuilder
from .renderer import TeardownRenderer

teardown = APIRouter(tags=["teardown"], prefix="/teardown")

builder = TeardownBuilder()
renderer = TeardownRenderer()


def build_initial_state(user_query: str) -> ProductQuestions:
    return {
        "user_query": user_query,
        "fully_answered": False,
        "follow_up_questions": [],
        "question_mapping": {},
        "product_context": "",
        "market_search_query": "",
        "market_analysis": [],
    }


@teardown.post("/")
async def generate_teardown(payload: QueryRequest):
    state = build_initial_state(payload.user_query)
    questions = run_product_pipeline(state)

    if not questions["fully_answered"]:
        return JSONResponse(
            status_code=200,
            content={
                "status": "needs_more_info",
                "follow_up_questions": questions["follow_up_questions"],
                "question_mapping": questions["question_mapping"],
            },
        )

    teardown_data = builder.build(questions)
    markdown = renderer.render(teardown_data)

    return PlainTextResponse(markdown)