# ShipIt

ShipIt turns a raw product idea into an **investor-grade teardown report** — automatically.

Founders waste weeks asking the wrong questions, cherry-picking data, and building products nobody needs. ShipIt fixes this by running any idea through a **rigorous, LLM-powered discovery pipeline** that forces you to think through every dimension of your product *before* you start coding.

---

## The Problem

Every great product starts as a raw idea. But between a founder's napkin sketch and a fundable business thesis lies a gap that typically requires weeks of research, multiple expert consultations, and expensive market analysis tools to bridge.

Most founders fall into one of these traps:

- **Analysis paralysis** — They don't know which questions to ask, so they never start.
- **Confirmation bias** — They only seek evidence that validates their idea and ignore risks.
- **Surface-level research** — A quick Google search and a Notion doc does not replace rigorous competitive analysis.
- **Expensive dead ends** — Building a product only to discover nobody actually needs it.

The core difficulty is not a lack of information — it's the **lack of a structured, repeatable system** that forces you to think through every dimension of a product idea *before* you start coding. ShipIt provides that system.

---

## What It Does

Drop in a product idea → ShipIt runs it through 3 phases:

1. **Product Discovery** — An LLM (Groq LLaMA) analyzes your idea against 6 fundamental questions: customer segment, pain point, frequency, current solution, advantage, and validation. The system doesn't ask all 6 upfront — it checks what's already answered in your input and only asks targeted follow-ups for what's missing. This creates a natural, conversational discovery loop that eliminates analysis paralysis.

2. **Market Intel** — Once all 6 questions are answered, ShipIt builds a search query from your product context and searches the web via Tavily for real competitors and market dynamics. The LLM then identifies specific, named competitors with reasoning grounded in actual search results — not generic industry guesses. If no real competitors are found, it says so clearly.

3. **Teardown Report** — With the full product context + market intelligence, a structured LLM call generates a `ProductTeardown` object (enforced via Pydantic schema) containing 15 fields: product name, one-liner, executive summary, target users, pain points, core features, user journey, competitors (with names and reasons), market positioning, business model, moats, opportunities, risks, and verdict. Output is available as **Markdown** (via Jinja2 template) and a **professionally styled PDF** (via fpdf2) with a cover page, auto-generated table of contents, and branded sections.

---

## Quick Start

```bash
# Install dependencies
pip install -r Backend/requirements.txt

# Set these in Backend/.env:
#   DATABASE_URL="postgresql://user:pass@localhost:5432/shipit"
#   GROQ_API_KEY="gsk_your_key"
#   TAVILY_API_KEY="tvly-your_key"

# Run the server
uvicorn Backend.main:app --reload
```

```bash
# Submit a product idea
curl -X POST http://localhost:8000/teardown/ \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "user_query": "AI mock interview platform for college placement season"}'

# If more info is needed, you'll get follow-up questions back.
# Submit again with more context until you get the full report.
```

API docs are auto-generated at `http://localhost:8000/docs`.

---

## Stack

| Category | Technology | Why |
|----------|-----------|-----|
| Framework | **FastAPI** (Python) | Async API server with automatic OpenAPI docs and Pydantic integration |
| Database | **PostgreSQL** + SQLAlchemy | Reliable relational storage for users and projects |
| Auth | **JWT** + **Argon2** (passlib) | Secure token-based auth with modern password hashing |
| LLM | **Groq** (llama-3.1-8b-instant) via LangChain | Fast inference for product analysis and structured teardown generation |
| Search | **Tavily API** | Web search optimized for AI agents — feeds real market data into the pipeline |
| Templates | **Jinja2** | Server-side Markdown rendering from structured teardown data |
| PDF | **fpdf2** | Programmatic PDF generation with cover page, TOC, headers, and styled sections |
| Validation | **Pydantic v2** | Strict schema enforcement for all request/response models and the LLM output |

---

## Key Design Decisions

**Structured Output over Free-Form Text** — The teardown builder uses `ChatGroq.with_structured_output(ProductTeardown)`, forcing the LLM to return a strictly typed Pydantic schema. This eliminates hallucinated markdown formatting and makes the output reliably renderable.

**Two-Pass PDF Generation** — Content is rendered twice: first to build a table of contents (collecting section headings and their page numbers), then again with the TOC inserted between the cover and content. This avoids forward-reference issues.

**Evidence-Grounded Analysis** — The LLM prompt explicitly forbids inventing facts. The market analysis section only includes competitors that were found in Tavily search results, not generic industry names.

**Graceful Fallbacks** — If the LLM call fails during product discovery, the system falls back to simple text heuristics (keyword matching) to extract whatever information it can from the user's input — ensuring the pipeline degrades gracefully rather than crashing.

---

## Structure

```
Backend/
├── main.py                   # FastAPI entrypoint — registers all 3 routers
├── db.py                     # PostgreSQL connection, session factory, Base
├── models/
│   └── user.py               # User & Project ORM models
├── schemas/
│   ├── auth.py               # Signup/Login request schemas
│   ├── query_schema.py        # Query request/response
│   └── teardown.py            # ProductTeardown + CompetitorItem Pydantic models
├── routes/
│   ├── auth/auth.py           # /signup, /login with JWT + Argon2
│   ├── query/
│   │   ├── query.py           # ✦ Discovery pipeline — the core engine
│   │   └── tavily_sdk.py      # Tavily client test script
│   └── teardown/
│       ├── template.py        # /teardown/ endpoint — orchestrates full pipeline
│       ├── builder.py         # LLM call with structured output → ProductTeardown
│       ├── renderer.py        # ProductTeardown → Jinja2 Markdown
│       ├── pdf_generator.py   # Markdown → professional PDF (fpdf2)
│       ├── prompts.py         # LLM system prompt for teardown generation
│       ├── flow.md            # Teardown content outline reference
│       └── template/
│           └── teardown.j2    # Jinja2 Markdown template
└── output/                    # Generated PDF files land here
```

---

## API Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|:------------:|-------------|
| `POST` | `/api/signup` | ❌ | Create account (email, name, password) |
| `POST` | `/api/login` | ❌ | Login → returns JWT access token |
| `POST` | `/api/query` | ✅ | Run product discovery pipeline |
| `GET` | `/api/query` | ✅ | Verify auth status |
| `POST` | `/teardown/` | ❌ | Full teardown — runs discovery + market intel + report generation |

---

## Pipeline Flow

```
User submits idea
       │
       ▼
┌─────────────────────────┐
│  Product Discovery      │
│  LLM checks 6 questions │──────── If incomplete → return follow-up questions
│  against user input     │
└─────────┬───────────────┘
          │ (all 6 answered)
          ▼
┌─────────────────────────┐
│  Product Context Gen    │
│  LLM writes structured  │
│  context document       │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Market Intel           │
│  Tavily search + LLM   │
│  identifies competitors │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Teardown Generation    │
│  Structured LLM →       │
│  ProductTeardown schema │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Rendering              │
│  Jinja2 (Markdown)  +  │────→ Markdown
│  fpdf2 (PDF)           │────→ PDF (cover, TOC, styled sections)
└─────────────────────────┘
```
