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
   - **Apify** (optional): deeper forum/review scraping for top 3 competitors when `APIFY_API_KEY` is set
   - Output is structured as `CustomerVoiceAnalysis`: current solutions, competitor sentiment, market gaps, and recommended features

4. **Teardown Report** — With full product context, market intel, and customer voice, a structured LLM call (Groq LLaMA 3.3 70B) generates a `ProductTeardown` object validated via Pydantic. Features and opportunities are **gap-driven** — tied to real competitor dissatisfaction, not generic founder assumptions.

Output is available as **Markdown** (Jinja2 template) and a **professionally styled PDF** (fpdf2) with cover page, auto-generated table of contents, and branded sections.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r Backend/requirements.txt
```

### 2. Configure environment

Create `Backend/.env`:

```env
DATABASE_URL="postgresql://user:pass@localhost:5432/shipit"
GROQ_API_KEY="gsk_your_key"
TAVILY_API_KEY="tvly-your_key"
SECRET_KEY="your-jwt-secret"          # optional, defaults to "change-me"

# Optional — enables deeper customer voice research for top 3 competitors
APIFY_API_KEY="apify_api_your_key"
```

### 3. Run the server

From the repo root:

```bash
uvicorn Backend.main:app --reload
```

API docs: `http://localhost:8000/docs`

### 4. Generate a PDF teardown

```bash
curl -X POST http://localhost:8000/teardown/generate-pdf \
  -H "Content-Type: application/json" \
  -d "{\"project_id\": 1, \"user_query\": \"AI mock interview platform for final-year engineering students preparing for campus placements. Target: college students in India. Pain: no realistic interview practice with actionable feedback. Frequency: every placement season. Current solutions: YouTube, LeetCode, peer mock interviews. Advantage: AI-generated questions, real-time evaluation, personalized improvement plan. Validation: 20 students expressed strong interest.\"}"
```

If discovery is incomplete, you'll get `follow_up_questions` back. Submit again with more context until you get the full report.

Response on success:

```json
{
  "status": "success",
  "product_name": "CampusMock AI",
  "pdf_filename": "CampusMock_AI_a1b2c3d4.pdf",
  "pdf_path": "Backend/output/CampusMock_AI_a1b2c3d4.pdf",
  "download_url": "/teardown/download/CampusMock_AI_a1b2c3d4.pdf"
}
```

Download the PDF:

```bash
curl -O http://localhost:8000/teardown/download/CampusMock_AI_a1b2c3d4.pdf
```

---

## Stack

| Category | Technology | Why |
|----------|-----------|-----|
| Framework | **FastAPI** (Python) | Async API server with automatic OpenAPI docs and Pydantic integration |
| Database | **PostgreSQL** + SQLAlchemy | Reliable relational storage for users and projects |
| Auth | **JWT** + **Argon2** (passlib) | Secure token-based auth with modern password hashing |
| LLM | **Groq** via LangChain | 8B for discovery/voice analysis; 70B for teardown generation |
| Search | **Tavily API** | Competitor discovery and per-competitor review/complaint research |
| Scraping | **Apify** (optional) | Deep web scraping for richer customer sentiment data |
| Templates | **Jinja2** | Server-side Markdown rendering from structured teardown data |
| PDF | **fpdf2** | Programmatic PDF generation with cover page, TOC, headers, and styled sections |
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
├── db.py                           # PostgreSQL connection, session factory, Base
├── models/
│   └── user.py                     # User & Project ORM models
├── schemas/
│   ├── auth.py                     # Signup/Login request schemas
│   ├── query_schema.py             # Query request/response
│   └── teardown.py                 # ProductTeardown, CustomerVoiceAnalysis, MarketGap, etc.
├── routes/
│   ├── auth/auth.py                # /api/signup, /api/login with JWT + Argon2
│   ├── query/
│   │   ├── query.py                # Discovery pipeline — the core engine (Phases 1–4)
│   │   └── tavily_sdk.py           # Tavily client test script
│   ├── customer/
│   │   ├── voice_analysis.py       # Phase 4: hybrid Tavily/Apify customer voice research
│   │   └── behaviour.py            # Dev-only /behaviour/debug endpoint
│   └── teardown/
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
| `POST` | `/api/query` | ✅ | Run full discovery pipeline (Phases 1–4); persists state to project |
| `GET` | `/api/query` | ✅ | Verify auth status |
| `POST` | `/teardown/` | ❌ | Full teardown → Markdown |
| `POST` | `/teardown/generate-pdf` | ❌ | Full teardown → PDF file in `Backend/output/` |
| `GET` | `/teardown/download/{filename}` | ❌ | Download a generated PDF |
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
│  Teardown Generation    │
│  LLM 70B → JSON →       │
│  ProductTeardown schema │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Rendering              │
│  Jinja2 → Markdown      │
│  fpdf2  → PDF           │
└─────────────────────────┘
```

---

## PDF Report Sections

The generated investor-ready PDF includes:

- One-Liner & Executive Summary
- Target Users, Pain Points, Core Features, User Journey
- Competitors
- **What Customers Use Today**
- **Competitor Satisfaction** (with evidence-backed complaints)
- **Market Gaps** (unmet needs + product opportunity)
- **How This Product Closes the Gap** (gap-driven features)
- Market Positioning, Business Model, Moats, Opportunities, Risks, Verdict

---

## Database Notes

If upgrading an existing database, add the new column:

```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS customer_voice JSON;
```

`Base.metadata.create_all()` only creates new tables — it does not alter existing ones.

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
