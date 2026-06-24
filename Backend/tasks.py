import os
import uuid
from celery_app import celery_app
from db import session_local
from models.user import User, Project
from routes.query.query import (
    build_pipeline_state_from_request,
    run_product_pipeline,
    persist_project_state,
)
from routes.teardown.builder import TeardownBuilder
from routes.teardown.renderer import TeardownRenderer
from routes.teardown.pdf_generator import md_to_pdf
from timing import PipelineTimer

builder = TeardownBuilder()
renderer = TeardownRenderer()

@celery_app.task(bind=True)
def generate_teardown_pdf_task(self, project_id: int, user_query: str, user_id: int):
    """
    Celery task to run the product pipeline and generate a teardown PDF in the background.
    """
    db = session_local()
    request_timer = PipelineTimer(label=f"celery_pdf_task_{self.request.id}")
    
    try:
        # 1. Fetch user to ensure context is correct (optional but good for consistency)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "detail": "User not found"}

        # 2. Build state and run pipeline
        state = build_pipeline_state_from_request(project_id, user_query, user_id, db)
        questions = run_product_pipeline(state, timer=request_timer, finalize_timer=False)
        persist_project_state(project_id, user_id, questions, db)

        # 3. Check if fully answered
        if not questions["fully_answered"]:
            timing = request_timer.finish()
            return {
                "status": "needs_more_info",
                "follow_up_questions": questions["follow_up_questions"],
                "question_mapping": questions["question_mapping"],
                "timing": timing,
            }

        # 4. Build Markdown
        try:
            teardown_data = builder.build(questions, timer=request_timer)
        except Exception as exc:
            return {"status": "error", "detail": f"Teardown generation failed: {exc}"}

        request_timer.start_phase("phase6_markdown_render")
        markdown = renderer.render(teardown_data)
        product_name = teardown_data.product_name

        # 5. Generate PDF
        request_timer.start_phase("phase6_pdf_generation")
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in product_name).strip().replace(" ", "_")
        if not safe_name:
            safe_name = "product_teardown"
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{safe_name}_{unique_id}.pdf"

        pdf_path = md_to_pdf(markdown, filename, teardown=teardown_data)
        timing = request_timer.finish()

        return {
            "status": "success",
            "product_name": product_name,
            "pdf_filename": filename,
            "pdf_path": str(pdf_path),
            "download_url": f"/teardown/download/{filename}",
            "timing": timing,
        }

    except Exception as e:
        return {"status": "error", "detail": str(e)}
    finally:
        db.close()
