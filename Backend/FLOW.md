# How ShipIt Works (Beginner Guide)

Think of ShipIt like a **factory assembly line**. You drop in a product idea at the front. It moves through stations. A PDF report comes out the back.

---

## The Big Picture (One Sentence)

**User sends idea → 4 research phases run → LLM writes a structured report → Jinja2 turns it into Markdown → fpdf2 turns that into a PDF.**

---

## Flow Diagram

```
YOU (curl / browser)
       │
       ▼
┌──────────────────┐
│  main.py         │  Front door — starts FastAPI, connects all routes
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  template.py     │  /teardown/generate-pdf — orchestrates everything
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  query.py        │  run_product_pipeline() — Phases 1–4
│  voice_analysis  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  builder.py      │  Phase 5 — LLM writes ProductTeardown JSON
│  renderer.py     │  Phase 6 — Markdown from template
│  pdf_generator   │  Phase 6 — PDF file on disk
└──────────────────┘
```

---

## File-by-File: What Lives Where

### Entry point

| File | Plain English |
|------|----------------|
| [`main.py`](main.py) | Turns the app ON. Registers routes: auth, query, teardown, behaviour. Creates DB tables on startup. |
| [`db.py`](db.py) | PostgreSQL connection. Every route that needs the DB uses `get_db()`. |
| [`timing.py`](timing.py) | Stopwatch for each pipeline phase. Prints `[TIMING]` lines you saw in the terminal. |

### Data shapes (Pydantic + SQLAlchemy)

| File | Plain English |
|------|----------------|
| [`schemas/query_schema.py`](schemas/query_schema.py) | What `/api/query` accepts (`project_id`, `user_query`) and returns. |
| [`schemas/teardown.py`](schemas/teardown.py) | The **report contract**: `ProductTeardown`, `CustomerVoiceAnalysis`, `MarketGap`, etc. The LLM must fill these fields. |
| [`schemas/auth.py`](schemas/auth.py) | Signup/login body shapes. |
| [`models/user.py`](models/user.py) | DB tables: `User` (account) and `Project` (saved discovery state per idea). |

### Routes (API endpoints)

| File | Endpoints | What it does |
|------|-----------|--------------|
| [`routes/auth/auth.py`](routes/auth/auth.py) | `POST /api/signup`, `POST /api/login` | Creates users, returns JWT token. |
| [`routes/query/query.py`](routes/query/query.py) | `POST /api/query` | **Core pipeline** (Phases 1–4). Requires login. Saves state to `Project`. |
| [`routes/teardown/template.py`](routes/teardown/template.py) | `POST /teardown/`, `POST /teardown/generate-pdf`, `GET /teardown/download/...` | Runs full pipeline + report + PDF. Returns `timing` in JSON. |
| [`routes/customer/voice_analysis.py`](routes/customer/voice_analysis.py) | (internal, not called directly) | **Phase 4** — searches reviews per competitor, finds gaps. |
| [`routes/customer/behaviour.py`](routes/customer/behaviour.py) | `POST /behaviour/debug` | Dev-only test for Phase 4 on one competitor. |

### Teardown generation (Phases 5–6)

| File | Plain English |
|------|----------------|
| [`routes/teardown/builder.py`](routes/teardown/builder.py) | Calls Groq 70B with all pipeline data. Gets back JSON → `ProductTeardown`. |
| [`routes/teardown/normalizer.py`](routes/teardown/normalizer.py) | Fixes messy LLM JSON (strings where arrays should be, etc.). |
| [`routes/teardown/prompts.py`](routes/teardown/prompts.py) | Instructions telling the LLM how to write the report. |
| [`routes/teardown/renderer.py`](routes/teardown/renderer.py) | Pours `ProductTeardown` data into the Jinja2 template → Markdown string. |
| [`routes/teardown/template/teardown.j2`](routes/teardown/template/teardown.j2) | HTML/Markdown **layout** of the report (sections, bullets). |
| [`routes/teardown/pdf_generator.py`](routes/teardown/pdf_generator.py) | Markdown → styled PDF with cover page and table of contents. |

### Output

| Path | Plain English |
|------|----------------|
| [`output/`](../output/) | Generated PDFs land here (local disk only — not scalable for production yet). |

---

## The 4 Pipeline Phases (in `query.py` + `voice_analysis.py`)

### Phase 1 — Product Discovery
- **File:** `query.py` → `analyze_product_answers()`
- **Input:** Your raw idea text
- **Output:** Which of 6 questions are answered; follow-up questions if not
- **External:** Groq 8B
- **Typical time:** ~0.5s

### Phase 2 — Product Context
- **File:** `query.py` → `generate_product_context()`
- **Input:** Answers from Phase 1
- **Output:** A structured summary document (text)
- **External:** Groq 8B
- **Typical time:** ~1s

### Phase 3 — Market Intel
- **File:** `query.py` → `generate_market_analysis()`
- **Input:** Product context
- **Output:** List of competitors (`comp_name`, `competitor_because`)
- **External:** Tavily search + Groq 8B
- **Typical time:** ~4s

### Phase 4 — Customer Voice (YOUR BOTTLENECK — was ~70%)
- **File:** `voice_analysis.py` → `generate_customer_voice()`
- **Input:** Product context + competitor list from Phase 3
- **Output:** `CustomerVoiceAnalysis` — who uses what, complaints, gaps, recommended features
- **External:** Tavily per competitor (parallel) + optional Apify + Groq 8B
- **Typical time:** Was ~26s; optimizations below target ~8–12s

### Phase 5 — Teardown LLM
- **File:** `builder.py`
- **Input:** Everything from Phases 1–4
- **Output:** Full `ProductTeardown` object
- **External:** Groq 70B
- **Typical time:** ~4s

### Phase 6 — Render + PDF
- **Files:** `renderer.py`, `pdf_generator.py`
- **Typical time:** <1s

---

## Phase 4 Speed Optimizations (just added)

Your timing showed **phase4_voice_competitor_research = 26s (70%)**. These env vars control the fast path:

| Env var | Default | What it does |
|---------|---------|--------------|
| `VOICE_COMPETITOR_LIMIT` | `3` | Only research top N competitors (not all 5+) |
| `VOICE_USE_APIFY` | `false` | Apify is slow (~20s+). Off by default. Set `true` for deeper scraping. |
| `TAVILY_VOICE_MAX_RESULTS` | `3` | Fewer search results per competitor = faster Tavily calls |

**In-memory Tavily cache:** Same competitor searched twice in one server session = instant cache hit (`[VOICE] Tavily cache HIT`).

For production scale, this cache moves to **Redis** (Step 5 in the scaling roadmap).

---

## What Happens When You Call `/teardown/generate-pdf`

1. `template.py` receives your JSON `{ project_id, user_query }`
2. Calls `run_product_pipeline()` in `query.py`
3. Phase 1: Are all 6 discovery questions answered? If not → return follow-up questions
4. Phases 2–4: Context → competitors → customer voice
5. `builder.py` writes the full teardown (Phase 5)
6. `renderer.py` + `teardown.j2` → Markdown
7. `pdf_generator.py` → PDF file in `output/`
8. Response includes `timing` breakdown + `download_url`

---

## Auth vs Public Endpoints

| Needs login? | Endpoints |
|--------------|-----------|
| Yes | `/api/query`, `/api/projects`, `/teardown/`, `/teardown/generate-pdf` |
| No | `/api/signup`, `/api/login`, `/teardown/download/{filename}`, `/behaviour/debug` |

**Scaling note:** Teardown routes now require JWT so strangers cannot burn your API credits.

---

## Config Files

| File | Purpose |
|------|---------|
| `Backend/.env` | Secrets: `GROQ_API_KEY`, `TAVILY_API_KEY`, `DATABASE_URL`, optional `APIFY_API_KEY` |
| `Backend/requirements.txt` | Python packages |

---

## Mental Model for Scaling

| Problem | Where it shows up | Future fix |
|---------|-------------------|------------|
| Slow requests | Phase 4 Tavily | Cache (done in-memory), competitor cap (done) |
| Timeouts | 37s+ PDF generation | Background job queue (Step 3) |
| PDFs lost on redeploy | `output/` folder | S3 / cloud storage (Step 4) |
| API abuse | Public teardown routes | Auth + rate limits (Step 2 + 5) |
| One server limit | Single uvicorn process | Docker + multiple workers (Step 6) |

---

## What to Read Next (in order)

1. [`routes/teardown/template.py`](routes/teardown/template.py) — see the full request path
2. [`routes/query/query.py`](routes/query/query.py) — search for `run_product_pipeline`
3. [`routes/customer/voice_analysis.py`](routes/customer/voice_analysis.py) — your bottleneck
4. [`routes/teardown/builder.py`](routes/teardown/builder.py) — how the final report is built

Run one PDF generation and follow the `[TIMING]` and `[VOICE]` log lines alongside this doc.
