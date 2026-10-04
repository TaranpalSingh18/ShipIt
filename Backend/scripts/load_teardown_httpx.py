"""
Lightweight load probe for teardown markdown endpoint using httpx.

What it does:
- Signup (idempotent) and login.
- Create one project.
- Fire N concurrent /teardown/ requests with a fully-answered query.
- Reports success count, failures, and latency stats.

Env vars:
  BASE_URL       (default http://localhost:8000)
  TEST_EMAIL     (default tester@example.com)
  TEST_PASSWORD  (default test1234)
  TEST_NAME      (default Test User)
  REQUESTS       (default 10)   # total requests
  CONCURRENCY    (default 5)    # simultaneous in-flight requests

Usage:
  python scripts/load_teardown_httpx.py

Note: This hits the markdown endpoint only (faster). PDF load testing would
spawn background Celery tasks and is heavier; keep counts low if you add it.
"""

import asyncio
import os
import statistics
import time
from typing import Any, Dict

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_EMAIL = os.getenv("TEST_EMAIL", "tester@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "test1234")
TEST_NAME = os.getenv("TEST_NAME", "Test User")
REQUESTS = int(os.getenv("REQUESTS", "10"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "5"))

FULL_QUERY = (
    "Targeting operations managers at mid-market retail brands. "
    "They struggle with frequent stockouts and overstock every month. "
    "Today they rely on spreadsheets, basic Shopify reports, and ad-hoc forecasts. "
    "Our solution delivers faster, more accurate forecasts with automatic reorder suggestions. "
    "Advantage is higher accuracy from blended POS + Shopify signals and proactive alerts. "
    "Validation: ran 8 pilot stores with measurable reductions in stockouts."
)


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def signup_if_needed(client: httpx.AsyncClient) -> None:
    payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME}
    resp = await client.post(f"{BASE_URL}/api/signup", json=payload)
    if resp.status_code in (200, 201):
        print("Signup ok")
        return
    if resp.status_code == 400 and "existing" in resp.text.lower():
        print("Signup skipped (user exists).")
        return
    resp.raise_for_status()


async def login(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        f"{BASE_URL}/api/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    resp.raise_for_status()
    token = resp.json().get("access_token", "")
    if not token:
        raise RuntimeError("No access_token in login response")
    return token


async def create_project(client: httpx.AsyncClient, token: str) -> int:
    resp = await client.post(
        f"{BASE_URL}/api/projects",
        json={"project_name": "LoadTest Project"},
        headers=_auth_headers(token),
    )
    resp.raise_for_status()
    project_id = resp.json().get("project_id")
    if not project_id:
        raise RuntimeError("No project_id returned")
    return project_id


async def call_teardown(client: httpx.AsyncClient, token: str, project_id: int) -> float:
    payload = {"project_id": project_id, "user_query": FULL_QUERY}
    started = time.perf_counter()
    resp = await client.post(
        f"{BASE_URL}/teardown/",
        json=payload,
        headers=_auth_headers(token),
    )
    latency = time.perf_counter() - started
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    # Markdown or JSON needs-more-info; treat 200 as success
    return latency


async def worker(queue: asyncio.Queue, client: httpx.AsyncClient, token: str, project_id: int, results: list[float], failures: list[str]):
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
        try:
            latency = await call_teardown(client, token, project_id)
            results.append(latency)
        except Exception as e:
            failures.append(str(e))
        finally:
            queue.task_done()


async def main() -> None:
    async with httpx.AsyncClient(timeout=120) as client:
        await signup_if_needed(client)
        token = await login(client)
        project_id = await create_project(client, token)

        queue: asyncio.Queue[Any] = asyncio.Queue()
        for _ in range(REQUESTS):
            queue.put_nowait(1)
        for _ in range(CONCURRENCY):
            queue.put_nowait(None)  # sentinel to stop each worker

        results: list[float] = []
        failures: list[str] = []

        workers = [
            asyncio.create_task(worker(queue, client, token, project_id, results, failures))
            for _ in range(CONCURRENCY)
        ]

        started = time.perf_counter()
        await queue.join()
        elapsed = time.perf_counter() - started

        for w in workers:
            w.cancel()

        print("\n=== Load Probe Results ===")
        print(f"Total requests: {REQUESTS}")
        print(f"Concurrency: {CONCURRENCY}")
        print(f"Wall time: {elapsed:.2f}s")
        print(f"Success: {len(results)}")
        print(f"Failures: {len(failures)}")

        if results:
            print(f"p50: {statistics.median(results):.2f}s")
            print(f"avg: {statistics.mean(results):.2f}s")
            print(f"p90: {statistics.quantiles(results, n=10)[8]:.2f}s")
            print(f"min: {min(results):.2f}s  max: {max(results):.2f}s")
        if failures:
            print("Sample failure:", failures[:3])


if __name__ == "__main__":
    asyncio.run(main())
