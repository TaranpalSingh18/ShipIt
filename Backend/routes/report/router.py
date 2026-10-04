import base64
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone

import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session

from celery_app import broker_url
from db import get_db
from models.user import Project, Report, User
from routes.query.query import get_current_user, get_user_project
from routes.report.render import OUTPUT_DIR
from tasks import build_report, generate_report_task

reports = APIRouter(prefix="/api", tags=["reports"])

# A memo that has not reported progress for this long was interrupted (worker restart, crash).
STALE_AFTER = timedelta(minutes=8)


def _expire_if_stale(report: Report, db: Session) -> Report:
    if report.status not in ("pending", "running"):
        return report
    touched = report.updated_at or report.created_at
    if touched and datetime.now(timezone.utc) - touched > STALE_AFTER:
        report.status = "failed"
        report.stage = "Interrupted"
        report.error = "The memo stopped before it finished, usually because the server restarted."
        db.commit()
    return report


def _broker_reachable() -> bool:
    try:
        client = redis.Redis.from_url(broker_url, socket_connect_timeout=0.4, socket_timeout=0.4)
        return bool(client.ping())
    except Exception:
        return False


def _fully_answered(project: Project) -> bool:
    mapping = project.question_mapping or {}
    return bool(mapping) and all(
        isinstance(value, dict) and value.get("answered") for value in mapping.values()
    ) and bool(project.product_context)


def _report_summary(report: Report | None) -> dict | None:
    if report is None:
        return None
    return {
        "id": report.id,
        "status": report.status,
        "progress": report.progress,
        "stage": report.stage,
        "error": report.error,
        "product_name": report.product_name,
        "verdict": report.verdict,
        "readiness": report.readiness,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


MEDIA_DIR = OUTPUT_DIR / "media"
DATA_URI = re.compile(r"^data:image/(png|jpeg);base64,(.+)$", re.S)


def externalize_media(report: Report, db: Session) -> None:
    """Move embedded logo/screenshot data URIs to files so the report JSON stays small.

    The PDF is rendered before this runs, so it keeps the images inline.
    """
    data = report.report_json or {}
    competitors = (data.get("competition") or {}).get("competitors") or []
    changed = False
    folder = MEDIA_DIR / report.id
    for index, comp in enumerate(competitors):
        for field in ("logo", "screenshot"):
            match = DATA_URI.match(comp.get(field) or "")
            if not match:
                continue
            ext = "png" if match.group(1) == "png" else "jpg"
            name = f"{field}_{index}.{ext}"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(base64.b64decode(match.group(2)))
            comp[field] = f"/api/reports/{report.id}/media/{name}"
            changed = True
    if changed:
        flag_modified(report, "report_json")
        db.commit()


def _owned_report(report_id: str, user: User, db: Session) -> Report:
    report = db.get(Report, report_id)
    if report is None or report.user_id != user.id:
        # Same answer for "missing" and "not yours", so ids can't be probed.
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@reports.get("/projects")
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.updated_at.desc().nullslast(), Project.id.desc())
        .all()
    )
    latest: dict[int, Report] = {}
    for report in (
        db.query(Report)
        .filter(Report.user_id == current_user.id)
        .order_by(Report.created_at.asc())
        .all()
    ):
        latest[report.project_id] = report

    return [
        {
            "id": project.id,
            "name": project.project_name,
            "idea": (project.latest_query or "").split("\n\nAdditional context:")[0][:280],
            "fully_answered": _fully_answered(project),
            "competitors": len(project.market_analysis or []),
            "updated_at": (project.updated_at or project.created_at).isoformat()
            if (project.updated_at or project.created_at)
            else None,
            "latest_report": _report_summary(latest.get(project.id)),
        }
        for project in projects
    ]


@reports.get("/projects/{project_id}")
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_user_project(project_id, current_user.id, db)
    history = (
        db.query(Report)
        .filter(Report.project_id == project.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return {
        "id": project.id,
        "name": project.project_name,
        "idea": (project.latest_query or "").split("\n\nAdditional context:")[0],
        "query_response": {
            "user_query": project.latest_query or "",
            "fully_answered": _fully_answered(project),
            "follow_up_questions": project.follow_up_questions or [],
            "question_mapping": project.question_mapping or {},
            "product_context": project.product_context or "",
            "market_analysis": project.market_analysis or [],
            "customer_voice": project.customer_voice or {},
        },
        "reports": [_report_summary(report) for report in history],
    }


@reports.post("/projects/{project_id}/reports", status_code=202)
def start_report(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_user_project(project_id, current_user.id, db)
    if not _fully_answered(project):
        raise HTTPException(status_code=409, detail="Answer the open questions before writing the memo.")

    running = (
        db.query(Report)
        .filter(Report.project_id == project.id, Report.status.in_(("pending", "running")))
        .first()
    )
    if running and _expire_if_stale(running, db).status != "failed":
        return _report_summary(running)

    report = Report(
        id=uuid.uuid4().hex,
        project_id=project.id,
        user_id=current_user.id,
        status="pending",
        progress=0,
        stage="Queued",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    if _broker_reachable():
        generate_report_task.delay(report.id)
    else:
        # No Redis: run in a background thread so the request returns at once.
        threading.Thread(target=build_report, args=(report.id,), daemon=True).start()
    return _report_summary(report)


@reports.get("/reports/{report_id}")
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = _expire_if_stale(_owned_report(report_id, current_user, db), db)
    if report.status == "success":
        externalize_media(report, db)
    summary = _report_summary(report)
    summary["project_id"] = report.project_id
    summary["report"] = report.report_json if report.status == "success" else None
    return summary


@reports.get("/reports/{report_id}/pdf")
def download_report_pdf(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = _owned_report(report_id, current_user, db)
    path = OUTPUT_DIR / (report.pdf_filename or "")
    if report.status != "success" or not report.pdf_filename or not path.is_file():
        raise HTTPException(status_code=404, detail="PDF not ready")
    return FileResponse(path=str(path), media_type="application/pdf", filename=report.pdf_filename)


@reports.get("/reports/{report_id}/media/{name}")
def report_media(report_id: str, name: str):
    """Competitor logos and screenshots. Unauthenticated so <img> tags can load them;
    the 128-bit report id in the path is the capability."""
    if not re.fullmatch(r"[0-9a-f]{32}", report_id) or not re.fullmatch(r"(logo|screenshot)_\d+\.(png|jpg)", name):
        raise HTTPException(status_code=404, detail="Not found")
    path = MEDIA_DIR / report_id / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(
        path,
        media_type="image/png" if name.endswith(".png") else "image/jpeg",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )
