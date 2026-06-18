# ShipIt

ShipIt turns a raw product idea into an **investor-grade teardown report** — automatically.

Founders waste weeks asking the wrong questions, cherry-picking data, and building products nobody needs. ShipIt fixes this by running any idea through a **rigorous, LLM-powered discovery pipeline** that forces you to think through every dimension of your product *before* you start coding.

## What It Does

Drop in a product idea → ShipIt runs it through 3 phases:

1. **Product Discovery** — An LLM checks your idea against 6 fundamental questions (customer segment, pain point, frequency, current solution, advantage, validation). If anything's missing, it asks targeted follow-ups — no more analysis paralysis.

2. **Market Intel** — Searches the web for real competitors and market context (via Tavily), then has the LLM identify specific competitors with reasoning grounded in actual data — not generic guesses.

3. **Teardown Report** — A structured LLM generates a professional report with: one-liner, executive summary, target users, pain points, core features, user journey, competitors, market positioning, business model, moats, opportunities, risks, and verdict. Output is both **Markdown** and a **styled PDF** with cover page, table of contents, and sections.

## Quick Start

```bash
pip install -r Backend/requirements.txt
# Set DATABASE_URL, GROQ_API_KEY, TAVILY_API_KEY in Backend/.env
uvicorn Backend.main:app --reload
```

```bash
curl -X POST http://localhost:8000/teardown/ \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "user_query": "AI mock interview platform for college placement season"}'
```

## Stack

**FastAPI** · **PostgreSQL** · **Groq (LLaMA)** · **Tavily** · **Jinja2** · **fpdf2** · **JWT + Argon2**

## Structure

```
Backend/
├── main.py                 # FastAPI entrypoint
├── models/user.py          # User & Project ORM
├── schemas/teardown.py     # Pydantic ProductTeardown schema
├── routes/
│   ├── auth/auth.py        # /signup, /login
│   ├── query/query.py      # ✦ Discovery pipeline (LLM + Tavily)
│   └── teardown/
│       ├── template.py     # /teardown/ orchestrator
│       ├── builder.py      # LLM → structured ProductTeardown
│       ├── renderer.py     # ProductTeardown → Jinja2 Markdown
│       ├── pdf_generator.py# Markdown → styled PDF
│       └── prompts.py      # LLM teardown prompt
└── output/                 # Generated PDFs
```

## Endpoints

| Method | Endpoint | Auth | What |
|--------|----------|------|------|
| POST | `/api/signup` | ❌ | Create account |
| POST | `/api/login` | ❌ | Login → JWT |
| POST | `/api/query` | ✅ | Run discovery pipeline |
| POST | `/teardown/` | ❌ | Generate full teardown report |