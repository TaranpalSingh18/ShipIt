import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

from schemas.query_schema import QueryRequest
from ..query.query import ProductQuestions

from ..query.query import run_product_pipeline
from .builder import TeardownBuilder
from .renderer import TeardownRenderer
from .pdf_generator import md_to_pdf, OUTPUT_DIR

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


@teardown.post("/generate-pdf")
async def generate_teardown_pdf(payload: QueryRequest):
    """
    Generate a full product teardown and save it as a PDF to the
    Backend/output/ directory.

    Returns a JSON response with:
      - status: "success" or "needs_more_info"
      - pdf_filename: name of the generated PDF file (if success)
      - pdf_path: relative path to the PDF file
      - product_name: name of the teardown product
      - download_url: URL path to download the PDF
    """
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

    # Generate teardown
    teardown_data = builder.build(questions)
    markdown = renderer.render(teardown_data)

    # Generate a unique filename
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in teardown_data.product_name).strip().replace(" ", "_")
    if not safe_name:
        safe_name = "product_teardown"
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{safe_name}_{unique_id}.pdf"

    # Save PDF to output directory
    pdf_path = md_to_pdf(markdown, filename)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "product_name": teardown_data.product_name,
            "pdf_filename": filename,
            "pdf_path": str(pdf_path),
            "download_url": f"/teardown/download/{filename}",
        },
    )


@teardown.get("/download/{filename}")
async def download_pdf(filename: str):
    """
    Download a generated PDF by filename from the Backend/output/ directory.
    """
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        return JSONResponse(
            status_code=404,
            content={"status": "error", "detail": "PDF file not found"},
        )

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(filepath),
        media_type="application/pdf",
        filename=filename,
    )
