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

Drop in a product idea → ShipIt runs it through **4 research phases**, then generates a teardown report:

1. **Product Discovery** — An LLM (Groq LLaMA 3.1 8B) analyzes your idea against 6 fundamental questions: customer segment, pain point, frequency, current solution, advantage, and validation. The system doesn't ask all 6 upfront — it checks what's already answered in your input and only asks targeted follow-ups for what's missing.

2. **Market Intel** — Once all 6 questions are answered, ShipIt builds a search query from your product context and searches the web via **Tavily** for real competitors. The LLM identifies specific, named competitors with reasoning grounded in actual search results — not generic industry guesses.

3. **Customer Voice & Gap Analysis** — For each competitor, ShipIt researches what customers use, whether they're satisfied, and where the gaps are:
   - **Tavily** (always): per-competitor review and complaint search
   - **Apify** (optional): deeper forum/review scraping when `VOICE_USE_APIFY=true` and `APIFY_API_KEY` is set (off by default for speed)
   - Output is structured as `CustomerVoiceAnalysis`: current solutions, competitor sentiment, market gaps, and recommended features

4. **Investor Memo** — With the product context, competitors and customer voice in hand, ShipIt researches further (market size and growth, each competitor's pricing, funding, founding year and HQ) and keeps every web result in a numbered source list. Four Groq calls write the memo in sections, and every number has to cite a source: figures without one are replaced with "Not found" rather than estimated. Competitor logos and homepage screenshots are captured with headless Chromium.

The memo is a **12-page A4 PDF** (HTML + SVG rendered by Chromium) and the same content as an **interactive report** in the web app: sortable competitor tables, a hoverable positioning map, a value-proposition canvas that links each pain to its reliever, a risk heatmap, a scorecard radar and a sources drawer.

![Architecture Diagram](Backend/output/arch.png)
---

## Quick Start

### 1. Install dependencies

```bash
pip install -r Backend/requirements.txt
```

### 2. Configure environment

Create `Backend/.env` with your keys (see variables below).

```env
DATABASE_URL="postgresql://user:pass@localhost:5432/shipit"
GROQ_API_KEY="gsk_your_key"
TAVILY_API_KEY="tvly-your_key"
SECRET_KEY="your-jwt-secret"          # optional, defaults to "change-me"

# Optional — deeper research (slow). Requires APIFY_API_KEY + VOICE_USE_APIFY=true
APIFY_API_KEY="apify_api_your_key"
VOICE_USE_APIFY="false"
VOICE_COMPETITOR_LIMIT="3"
TAVILY_VOICE_MAX_RESULTS="3"
```

See [`Backend/FLOW.md`](Backend/FLOW.md) for a beginner-friendly walkthrough of every file and how data flows through the pipeline.

### 3. Run the server (local, no Docker)

From the repo root:

```bash
uvicorn Backend.main:app --reload
```

API docs: `http://localhost:8000/docs`

### 3b. Run with Docker + Nginx (recommended for scaling)

From the repo root:

```bash
docker compose up --build
```

This will start:

- a `backend` FastAPI container on port 8000 (internal)
- a `celery` worker container for background PDF generation
- a `db` container (PostgreSQL)
- a `redis` container (Celery broker + result backend)
- an `nginx` reverse proxy on port 80

The Nginx container routes `http://localhost/` → `backend`.

To run multiple backend containers (horizontal scaling on one machine), use:

```bash
docker compose up --build --scale backend=3
```

Docker will load-balance requests from Nginx across the `backend` replicas.

### 4. Run database migrations (recommended)

From `Backend/`:

```bash
cd Backend
alembic upgrade head
```

For local dev only, you can skip Alembic and set `AUTO_CREATE_DB=true` in `.env` (default).

### 5. Write an investor memo

Run the frontend (`cd Frontend && npm install && npm run dev`) and use the app, or call the API.
First sign up, log in, create a project and answer the six questions with `POST /api/query`
until `fully_answered` is `true`. Then:

```bash
# Start the memo (returns a report id; runs on Celery when Redis is up, otherwise in a thread)
curl -X POST http://localhost:8000/api/projects/1/reports -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Poll progress, then read the memo JSON when status is "success"
curl http://localhost:8000/api/reports/REPORT_ID -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Download the PDF
curl -o memo.pdf http://localhost:8000/api/reports/REPORT_ID/pdf -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

To iterate on the memo design without any LLM calls, render the bundled fixture:

```bash
cd Backend
playwright install chromium          # once
python scripts/render_sample_report.py --png   # → output/sample_report.pdf + output/sample_pages/*.png
```

---

## Stack

| Category | Technology | Why |
|----------|-----------|-----|
| Framework | **FastAPI** (Python) | Async API server with automatic OpenAPI docs and Pydantic integration |
| Database | **PostgreSQL** + SQLAlchemy | Reliable relational storage for users and projects |
| Auth | **JWT** + **Argon2** (passlib) | Secure token-based auth with modern password hashing |
| LLM | **Groq** via LangChain | `gpt-oss-120b` and `gpt-oss-20b`; memo sections are split across both to stay inside per-model rate limits |
| Search | **Tavily API** | Competitor discovery and per-competitor review/complaint research |
| Scraping | **Apify** (optional) | Deep web scraping for richer customer sentiment data |
| Templates | **Jinja2** | Server-side HTML for the investor memo |
| PDF & capture | **Playwright (Chromium)** | Prints the HTML memo to PDF; captures competitor homepages |
| Frontend | **React 19 + Vite**, React Router | Landing, case dashboard, workspace and interactive report |
| Validation | **Pydantic v2** | Strict schema enforcement for all request/response models |

---

## Key Design Decisions

**Gap-Driven Features** — `core_features` and `opportunities` in the teardown are explicitly tied to `CustomerVoiceAnalysis` market gaps and competitor complaints, not invented from the founder's idea alone.

**Hybrid Customer Research** — Tavily runs for every competitor (fast, always-on). Apify deep-scrapes only the top 3 when configured, keeping cost and latency bounded.

**Robust JSON Parsing** — Teardown generation uses explicit JSON prompts with a normalizer layer that coerces malformed LLM output (strings → lists, competitor fallbacks from market data) before Pydantic validation. This avoids brittle Groq tool-calling failures on complex nested schemas.

**Two-Pass PDF Generation** — Content is rendered twice: first to build a table of contents, then again with the TOC inserted between the cover and content.

**Evidence-Grounded Analysis** — Prompts forbid inventing facts. Competitors come from Tavily results; satisfaction signals require evidence from search/scrape data or are marked unknown.

**Graceful Fallbacks** — Discovery falls back to keyword heuristics if the LLM parse fails. Teardown generation retries once on JSON parse failure.

---

## Project Structure

```
Backend/
├── main.py                         # FastAPI entrypoint — registers all routers
├── alembic/                        # Database migrations (Alembic)
│   └── versions/
├── db.py                           # PostgreSQL connection, session factory, Base
├── models/
│   └── user.py                     # User & Project ORM models
├── schemas/
│   ├── auth.py                     # Signup/Login request schemas
│   ├── query_schema.py             # Query request/response
│   ├── teardown.py                 # ProductTeardown, CustomerVoiceAnalysis, MarketGap, etc.
│   └── report.py                   # InvestorReport — the memo schema
├── routes/
│   ├── auth/auth.py                # /api/signup, /api/login with JWT + Argon2
│   ├── query/
│   │   ├── query.py                # Discovery pipeline — the core engine (Phases 1–4)
│   │   └── tavily_sdk.py           # Tavily client test script
│   ├── customer/
│   │   ├── voice_analysis.py       # Phase 4: hybrid Tavily/Apify customer voice research
│   │   └── behaviour.py            # Dev-only /behaviour/debug endpoint
│   ├── research/
│   │   ├── market_research.py      # Tavily searches + numbered SourceRegistry
│   │   └── competitor_assets.py    # Logos (favicon service) + homepage screenshots
│   ├── report/
│   │   ├── router.py               # /api/projects, /api/reports endpoints
│   │   ├── generator.py            # 4 section LLM calls + source validation → InvestorReport
│   │   ├── prompts.py              # Section prompts
│   │   ├── charts.py               # SVG charts (ring, TAM circles, positioning map, radar)
│   │   ├── render.py               # HTML → PDF with Chromium (auto-fits each page)
│   │   └── templates/              # report.html.j2 + report.css (12-page memo)
│   └── teardown/                   # Legacy one-pager (no longer mounted in main.py)
│       ├── template.py             # /teardown/ endpoints — orchestrates full pipeline
│       ├── builder.py              # LLM teardown generation → ProductTeardown
│       ├── normalizer.py           # JSON parse + coerce malformed LLM output
│       ├── renderer.py             # ProductTeardown → Jinja2 Markdown
│       ├── pdf_generator.py        # Markdown → professional PDF (fpdf2)
│       ├── prompts.py              # LLM prompts for teardown generation
│       ├── flow.md                 # Teardown content outline reference
│       └── template/
│           └── teardown.j2         # Jinja2 Markdown template
└── output/                         # Generated PDF files land here
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| `POST` | `/api/signup` | ❌ | Create account (email, name, password) |
| `POST` | `/api/login` | ❌ | Login → returns JWT access token |
| `POST` | `/api/projects` | ✅ | Create a project → returns `project_id` |
| `POST` | `/api/query` | ✅ | Run full discovery pipeline (Phases 1–4); persists state to project |
| `GET` | `/api/query` | ✅ | Verify auth status |
| `GET` | `/api/projects` | ✅ | List your cases with their latest memo |
| `GET` | `/api/projects/{id}` | ✅ | One case: discovery state and memo history |
| `POST` | `/api/projects/{id}/reports` | ✅ | Start writing the investor memo (202) |
| `GET` | `/api/reports/{id}` | ✅ | Memo status, progress and, when done, the full memo JSON |
| `GET` | `/api/reports/{id}/pdf` | ✅ | Download the memo PDF (owner only) |
| `GET` | `/api/reports/{id}/media/{file}` | ❌ | Competitor logo/screenshot (the report id is the capability) |
| `POST` | `/behaviour/debug` | ❌ | Dev-only: test customer voice for one competitor |

---

## Pipeline Flow

```
User submits idea
       │
       ▼
┌─────────────────────────┐
│  Phase 1: Discovery     │
│  LLM checks 6 questions │──────── If incomplete → return follow-up questions
└─────────┬───────────────┘
          │ (all 6 answered)
          ▼
┌─────────────────────────┐
│  Phase 2: Product       │
│  Context Generation     │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Phase 3: Market Intel  │
│  Tavily + LLM           │
│  → named competitors    │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Phase 4: Customer      │
│  Voice & Gap Analysis   │
│  Tavily per competitor  │
│  + Apify (optional)     │
│  → gaps & features      │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Memo research          │
│  market size, pricing,  │
│  funding → numbered     │
│  sources, logos, shots  │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Memo writing           │
│  4 section LLM calls →  │
│  InvestorReport; drop   │
│  unsourced numbers      │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Rendering              │
│  Jinja2 + SVG → HTML    │
│  Chromium → 12-page PDF │
│  + interactive web view │
└─────────────────────────┘
```

---

## Investor Memo Pages

1. **Executive one-pager** — verdict, readiness score, TAM, growth, why invest, key risks
2. **Problem & customer** — pains with severity and real user quotes, segments, why now
3. **Value proposition** — Strategyzer canvas with pain → reliever and gain → creator fit map, before/after, user journey
4. **Market** — TAM/SAM/SOM with method, confidence and sources; CAGR; sizing logic; trends
5. **Competitive landscape** — homepage screenshot, logo, founded, HQ, funding, pricing, satisfaction, top complaint
6. **Head-to-head** — feature matrix, positioning map with a reason for every placement, why we win
7. **Voice of the customer** — sentiment per competitor, complaint themes, gaps → our angle
8. **Business model & GTM** — pricing tiers vs competitor pricing, unit-economics assumptions, channels
9. **Risks & moats** — likelihood × impact heatmap with mitigations, moat strength, opportunities
10. **Verdict** — five-part scorecard radar, reasoning, bottom line
11. **Next 90 days** — milestones with metrics and targets, investor Q&A
12. **Sources** — every page read, cited ones highlighted

---

## Database Notes

**Alembic migrations** (from `Backend/`):

```bash
alembic upgrade head    # apply migrations
alembic revision --autogenerate -m "describe change"  # after model changes
```

Set `AUTO_CREATE_DB=false` in production and use Alembic only.

If upgrading an old database without Alembic history:

```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS customer_voice JSON;
```

---

## Example Use Case

**Input:** *"AI mock interview platform for college placements"*

**Pipeline output:**
- **Competitors:** Pramp, InterviewBit, LeetCode (from Tavily)
- **Customer voice:** "Pramp users complain about limited question variety" / "InterviewBit feels too DSA-heavy for behavioral rounds"
- **Gap:** No tool combines AI behavioral mock interviews tailored to Indian campus placement formats
- **Feature:** Campus-specific behavioral AI interviewer with company-wise question banks
- **PDF:** Full investor teardown with gap evidence and positioning

---

## License

MIT (or add your license here)
