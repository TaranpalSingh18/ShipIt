import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from db import get_db
from models.user import User
from schemas.query_schema import QueryRequest
from schemas.teardown import ProductTeardown
from ..query.query import (
    ProductQuestions,
    build_pipeline_state_from_request,
    get_current_user,
    persist_project_state,
    run_product_pipeline,
)
from .builder import TeardownBuilder
from .renderer import TeardownRenderer
from .pdf_generator import md_to_pdf, OUTPUT_DIR
from timing import PipelineTimer

teardown = APIRouter(tags=["teardown"], prefix="/teardown")

builder = TeardownBuilder()
renderer = TeardownRenderer()


def _build_teardown_markdown(
    questions: ProductQuestions,
    timer: PipelineTimer | None = None,
) -> tuple[str, str, ProductTeardown]:
    try:
        teardown_data = builder.build(questions, timer=timer)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Teardown generation failed: {exc}",
        ) from exc

    if timer:
        timer.start_phase("phase6_markdown_render")
    markdown = renderer.render(teardown_data)
    return teardown_data.product_name, markdown, teardown_data


def _run_pipeline_for_request(
    payload: QueryRequest,
    current_user: User,
    db: Session,
    request_timer: PipelineTimer,
) -> ProductQuestions:
    state = build_pipeline_state_from_request(
        payload.project_id,
        payload.user_query,
        current_user.id,
        db,
    )
    questions = run_product_pipeline(state, timer=request_timer, finalize_timer=False)
    persist_project_state(payload.project_id, current_user.id, questions, db)
    return questions


@teardown.post("/")
async def generate_teardown(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request_timer = PipelineTimer(label="teardown_markdown_request")
    questions = _run_pipeline_for_request(payload, current_user, db, request_timer)

    if not questions["fully_answered"]:
        timing = request_timer.finish()
        return JSONResponse(
            status_code=200,
            content={
                "status": "needs_more_info",
                "follow_up_questions": questions["follow_up_questions"],
                "question_mapping": questions["question_mapping"],
                "timing": timing,
            },
        )

    product_name, markdown, _ = _build_teardown_markdown(questions, timer=request_timer)
    timing = request_timer.finish()
    print(f"[TIMING] Teardown markdown ready for: {product_name}")

    response = PlainTextResponse(markdown)
    response.headers["X-Pipeline-Timing-Total-S"] = str(timing["total_s"])
    return response


@teardown.post("/generate-pdf")
async def generate_teardown_pdf(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a full product teardown and save it as a PDF to the
    Backend/output/ directory. Requires JWT authentication.
    """
    request_timer = PipelineTimer(label="teardown_pdf_request")
    questions = _run_pipeline_for_request(payload, current_user, db, request_timer)

    if not questions["fully_answered"]:
        timing = request_timer.finish()
        return JSONResponse(
            status_code=200,
            content={
                "status": "needs_more_info",
                "follow_up_questions": questions["follow_up_questions"],
                "question_mapping": questions["question_mapping"],
                "timing": timing,
            },
        )

    product_name, markdown, teardown_data = _build_teardown_markdown(questions, timer=request_timer)

    request_timer.start_phase("phase6_pdf_generation")
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in product_name).strip().replace(" ", "_")
    if not safe_name:
        safe_name = "product_teardown"
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{safe_name}_{unique_id}.pdf"

    pdf_path = md_to_pdf(markdown, filename, teardown=teardown_data)
    timing = request_timer.finish()

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "product_name": product_name,
            "pdf_filename": filename,
            "pdf_path": str(pdf_path),
            "download_url": f"/teardown/download/{filename}",
            "timing": timing,
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
