import re

from celery_app import celery_app
from db import session_local
from models.user import Project, Report
from routes.report.generator import generate_report
from routes.report.render import render_pdf


def _set(report_id: str, **fields) -> None:
    """Write report progress in its own short session so pollers see it at once."""
    db = session_local()
    try:
        db.query(Report).filter(Report.id == report_id).update(fields)
        db.commit()
    finally:
        db.close()


def project_state(project: Project) -> dict:
    return {
        "user_query": project.latest_query or "",
        "question_mapping": project.question_mapping or {},
        "product_context": project.product_context or "",
        "market_analysis": project.market_analysis or [],
        "customer_voice": project.customer_voice or {},
    }


def build_report(report_id: str) -> dict:
    """Generate the investor memo for an existing Report row. Used by Celery and inline."""
    db = session_local()
    try:
        report = db.get(Report, report_id)
        if report is None:
            return {"status": "error", "detail": "Report not found"}
        project = db.get(Project, report.project_id)
        state = project_state(project)
    finally:
        db.close()

    _set(report_id, status="running", progress=3, stage="Starting")

    def progress(step: str, pct: int, label: str) -> None:
        _set(report_id, progress=pct, stage=label)

    try:
        memo = generate_report(state, progress=progress)
        progress("pdf", 90, "Designing the PDF")
        name = re.sub(r"[^A-Za-z0-9]+", "_", memo.narrative.product_name).strip("_") or "investor_memo"
        filename = f"{name}_{report_id[:8]}.pdf"
        render_pdf(memo, filename)
    except Exception as exc:
        detail = str(exc).encode("ascii", "backslashreplace").decode()[:500]
        print("[REPORT] generation failed:", detail)
        _set(report_id, status="failed", stage="Failed", error=detail)
        return {"status": "error", "detail": detail}

    _set(
        report_id,
        status="success",
        progress=100,
        stage="Done",
        product_name=memo.narrative.product_name,
        verdict=memo.strategy.verdict.label,
        readiness=memo.meta.readiness,
        report_json=memo.model_dump(mode="json"),
        pdf_filename=filename,
    )
    return {"status": "success", "report_id": report_id}


@celery_app.task(bind=True)
def generate_report_task(self, report_id: str):
    return build_report(report_id)
