from fastapi import  APIRouter
from fastapi.responses import PlainTextResponse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

teardown = APIRouter(tags=["teardonw"], prefix="/teardown")

BASE_DIR = Path(__file__).parent

environ = Environment(loader=FileSystemLoader(BASE_DIR / "template"))

@teardown.get('/')
async def get_template():
    data = {
        "product_name": "Interview Coach AI",
        "overview": "AI-powered interview preparation platform.",
        "target_users": [
            "College Students",
            "Job Seekers"
        ],
        "pain_points": [
            "Lack of feedback",
            "No realistic mock interviews"
        ]
    }

    template = environ.get_template("teardown.j2")

    rendered = template.render(**data)

    return PlainTextResponse(rendered)
