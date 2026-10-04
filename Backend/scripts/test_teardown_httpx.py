"""
Quick manual test for the teardown maker API using httpx.

Usage:
  1) Start the backend (e.g., uvicorn main:app --reload).
  2) If using background PDFs, also start Celery:
       celery -A celery_app worker --loglevel=info -P solo
  3) Install deps if needed: pip install httpx python-dotenv
  4) Run: python scripts/test_teardown_httpx.py
Env vars:
  BASE_URL       (default http://localhost:8000)
  TEST_EMAIL     (default tester@example.com)
  TEST_PASSWORD  (default test1234)
  TEST_NAME      (default Test User)
"""

import asyncio
import os
from typing import Any, Dict

import httpx
from dotenv import load_dotenv


load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_EMAIL = os.getenv("TEST_EMAIL", "tester@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "test1234")
TEST_NAME = os.getenv("TEST_NAME", "Test User")


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def signup_if_needed(client: httpx.AsyncClient) -> None:
    payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME}
    resp = await client.post(f"{BASE_URL}/api/signup", json=payload)
    if resp.status_code in (200, 201):
        print("Signup ok:", resp.json())
        return
    if resp.status_code == 400 and "existing" in resp.text.lower():
        print("Signup skipped (user exists).")
        return
    resp.raise_for_status()


async def login(client: httpx.AsyncClient) -> str:
    data = {"username": TEST_EMAIL, "password": TEST_PASSWORD}
    resp = await client.post(f"{BASE_URL}/api/login", data=data)
    resp.raise_for_status()
    token = resp.json().get("access_token", "")
    if not token:
        raise RuntimeError("No access_token in login response")
    print("Login ok.")
    return token


async def create_project(client: httpx.AsyncClient, token: str) -> int:
    resp = await client.post(
        f"{BASE_URL}/api/projects",
        json={"project_name": "HTTPX Teardown Test"},
        headers=_auth_headers(token),
    )
    resp.raise_for_status()
    project_id = resp.json().get("project_id")
    if not project_id:
        raise RuntimeError("No project_id returned")
    print("Project created:", project_id)
    return project_id


async def run_teardown_markdown(
    client: httpx.AsyncClient, token: str, project_id: int, user_query: str
) -> None:
    payload = {"project_id": project_id, "user_query": user_query}
    resp = await client.post(
        f"{BASE_URL}/teardown/",
        json=payload,
        headers=_auth_headers(token),
    )
    print("Markdown status:", resp.status_code)
    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith(
        "text/plain"
    ):
        print("Received Markdown preview (truncated to 800 chars):")
        print(resp.text[:800])
    else:
        print("JSON response:", resp.json())


async def run_teardown_pdf(
    client: httpx.AsyncClient, token: str, project_id: int, user_query: str
) -> None:
    payload = {"project_id": project_id, "user_query": user_query}
    start = await client.post(
        f"{BASE_URL}/teardown/generate-pdf",
        json=payload,
        headers=_auth_headers(token),
    )
    start.raise_for_status()
    data: Dict[str, Any] = start.json()
    task_id = data.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id returned: {data}")
    print("PDF task started:", task_id)

    # Poll until finished
    status = "PENDING"
    while status in ("PENDING", "STARTED"):
        await asyncio.sleep(2)
        poll = await client.get(f"{BASE_URL}/teardown/task/{task_id}")
        poll.raise_for_status()
        result = poll.json()
        status = result.get("status")
        print("Task status:", status)
        if status in ("SUCCESS", "FAILURE") or status not in ("PENDING", "STARTED"):
            print("Final task payload:", result)
            break


async def main() -> None:
    # Fully answers all six discovery questions to avoid follow-ups.
    user_query = (
        "Targeting operations managers at mid-market retail brands. "
        "They struggle with frequent stockouts and overstock every month. "
        "Today they rely on spreadsheets, basic Shopify reports, and ad-hoc forecasts. "
        "Our solution delivers faster, more accurate forecasts with automatic reorder suggestions. "
        "Advantage is higher accuracy from blended POS + Shopify signals and proactive alerts. "
        "Validation: ran 8 pilot stores with measurable reductions in stockouts."
    )

    async with httpx.AsyncClient(timeout=60) as client:
        await signup_if_needed(client)
        token = await login(client)
        project_id = await create_project(client, token)

        print("\n=== Markdown teardown ===")
        await run_teardown_markdown(client, token, project_id, user_query)

        print("\n=== PDF teardown (background task) ===")
        await run_teardown_pdf(client, token, project_id, user_query)


if __name__ == "__main__":
    asyncio.run(main())
