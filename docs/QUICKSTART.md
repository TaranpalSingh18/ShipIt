# ShipIt Quick Start Workflows

This guide walks through common workflows step-by-step.

---

## Workflow 1: Generate Your First Memo (5 minutes)

### Step 1: Sign up
1. Visit `http://localhost:5173`
2. Click **Sign up**
3. Enter email, name, password
4. Click **Create account**

### Step 2: Create a case
1. Click **New case** (or on the landing page)
2. Write a product name: e.g., "MockPath"
3. Write a one-liner: e.g., "AI mock interview platform for campus placements"
4. Click **Create case**

### Step 3: Answer 6 questions
1. **Who is for**: "Final-year engineering students preparing for placements"
2. **The pain**: "Students struggle with mock interviews; no structured practice"
3. **How often**: "Students interview 2–3 times per placement season"
4. **What they use now**: "Unstructured peer practice, generic coding platforms"
5. **Why this is better**: "AI gives instant feedback, company-specific questions, behavioral coaching"
6. **What you've checked**: "Interviewed 15 students, 80% would pay ₹99/month"

Click **Save** after each question. The form auto-saves.

### Step 4: Watch the memo generate
1. Once all 6 questions are answered, click **Write the investor memo**
2. Watch the progress bar stream through:
   - Researching competitors (8%)
   - Sizing the market (30%)
   - Capturing logos and homepages (75%)
   - Designing the PDF (90%)
   - Done (100%)
3. Total time: 60–90 seconds

### Step 5: Read the memo
1. Once done, the memo appears in the report view
2. Scroll through the 12 pages in the browser
3. Hover over charts (positioning map, risk heatmap, radar) to see details
4. Click footnote numbers `[1]`, `[2]`, etc. to see sources
5. Click **Download PDF** to save for investors/advisors

---

## Workflow 2: Compare Two Ideas

### Step 1: Create two cases
1. From the dashboard, click **New case**
2. Create "Idea A" with its questions
3. Generate memo for Idea A
4. Click **New case** again
5. Create "Idea B" with different answers
6. Generate memo for Idea B

### Step 2: Side-by-side comparison
1. Open Idea A memo in one browser tab
2. Open Idea B memo in another tab
3. Compare page-by-page:
   - **Page 1**: Which has a higher readiness score? Stronger verdict?
   - **Page 5**: Which has fewer, stronger competitors?
   - **Page 4**: Which market is bigger?
   - **Page 10**: Which has a clearer 90-day plan?
4. Note: Use the sources (page 12) to verify which memo is better researched

---

## Workflow 3: Refine Your Idea (Iterate)

### Step 1: Review feedback
1. Read the memo
2. Note any sections with "Not found" or low confidence
3. Identify assumptions you want to validate

### Step 2: Revise answers
1. Go back to the case workspace
2. Click on a question (e.g., "The pain")
3. Edit the answer with new insights
4. Click **Update**

### Step 3: Generate a new version
1. Click **Write a new version** (button on the report)
2. Watch the new memo generate (60–90 seconds)
3. Compare page-by-page with the previous version
4. See if:
   - Readiness score improved?
   - New market data appeared?
   - Competitive landscape changed?

Repeat 2–3 times until you're satisfied.

---

## Workflow 4: Share a Memo with Your Team

### Option A: Download PDF
1. Open the memo in the report view
2. Click **Download PDF** at the top
3. Send the PDF via email or Slack
4. Works offline—no account needed to read

### Option B: Share the web report
1. Copy the URL from your browser: `http://localhost:5173/app/report/REPORT_ID`
2. Share with team members (they need to log in to view)

### Option C: Present from the browser
1. Open the memo in the report view
2. Read on desktop (1440px) for full detail
3. Use the TOC (left sidebar) to jump between sections
4. Hover charts to show interactive features

---

## Workflow 5: Debug a Missing Market Size

### Problem
The memo says "TAM: Not found" on page 4.

### Why this happens
- Market research didn't find sourced data for your category
- Search terms were too specific or generic

### Solution
1. Go back to the case workspace
2. Edit "The pain" or "Who is for" to add:
   - Geography: "India", "US", "Global"
   - Industry: "EdTech", "Enterprise", "B2B SaaS"
   - Market term: "interview prep", "placement services"
3. Generate a new version
4. Memo will search with richer context

### Manual fallback
If memo still says "Not found":
1. Search `Tavily` manually: https://tavily.com/search
2. Find the TAM from analyst reports
3. Note the source (analyst name, URL, year)
4. Document in the memo as a future research note

---

## Workflow 6: Review the Competitive Landscape

### Page 5: Competitor Cards

Each card shows:
- **Logo** — Company brand identity
- **Screenshot** — Live homepage as of memo generation date
- **Founded** — Year, shows if new entrant or established player
- **HQ** — Geographic presence
- **Funding** — Latest round raised (shows traction)
- **Pricing** — Their tier that competes with yours (comparison point)
- **Satisfaction** — Star rating from customer reviews
- **Top complaint** — #1 reason customers churn (your opportunity)

### How to use this
1. Scan the "Top complaint" column
2. If multiple competitors have the same complaint (e.g., "no API"), that's your feature
3. Look at "Satisfaction" — lower stars = unhappy customers = market opportunity
4. Check "Pricing" — undercut them on price? Offer more features at same price?

### If a competitor is missing
1. The memo found fewer than 5 competitors (market may be small)
2. Or Playwright couldn't screenshot their homepage (blocked/down page)
3. Fallback: logo only, no screenshot
4. Manual fix: edit the question "What they use now" to add the missing competitor name

---

## Workflow 7: Validate Your 90-Day Plan

### Page 10: Milestones

The memo suggests 3-month validation plan:

**Month 1 (Days 1–30)**: Core validations
- Interview 20 customers
- Validate willingness to pay
- Build MVP core feature

**Month 2 (Days 31–60)**: Product-market fit
- Launch beta with 50 users
- Measure NPS and retention
- Refine based on feedback

**Month 3 (Days 61–90)**: Go/no-go gate
- Decide: scale up or pivot?
- Set criteria upfront (e.g., "60% monthly retention = go")

### How to use this
1. Read the milestone section
2. Replace with your actual plan (these are suggestions)
3. Add specific metrics: "20 customers interviewed" → "Interview customers in [industry]"
4. Share with your team and advisors
5. Check in monthly: are you on track?

---

## Workflow 8: Find Sources for a Specific Claim

### Page 12: Sources (Bibliography)

Each source is numbered and lists:
- **Title** — Exact webpage title
- **Domain** — Company/publication
- **URL** — Clickable link

### In-memo footnotes
- Page 4, TAM claim: click `[31]` to see the Gartner report
- Page 5, competitor funding: click `[15]` to see Crunchbase listing
- Page 7, customer complaint: click `[42]` to see the Amazon review

### How to verify
1. Click a source link
2. Skim the page to confirm the number (e.g., "market is $5.2B")
3. Note the date (older data = lower confidence)
4. If the page is down/blocked, search manually for the same statistic

---

## Workflow 9: Export the Memo for Investors

### Best practices

**PDF to email:**
- File size: ~2–3 MB (all images embedded)
- Send with a one-sentence intro: "Here's our investor memo for [Product]. We'd love your feedback."
- Follow up in 1 week if no response

**PDF to investors:**
- Mark as "Confidential" (footer already says this)
- Add a cover email with:
  - Who you are
  - Why you're reaching out (warm intro? cold email?)
  - What you're raising (if applicable)
  - Next step (30-min call?)

**Web report to advisors:**
- Share the URL
- They can explore interactively (hover charts, sort tables)
- Requires login (keeps it internal)

---

## Workflow 10: Troubleshoot a Failed Memo

### Problem: Memo shows "status: failed"

### Check these

1. **Is Redis running?**
   ```bash
   redis-cli ping
   # Should return PONG
   ```

2. **Is Celery worker running?**
   ```bash
   # Terminal check
   celery -A celery_app worker --loglevel=info
   # Should show "ready to accept tasks"
   ```

3. **Check database for error**
   ```sql
   SELECT id, status, error FROM reports WHERE status='failed' LIMIT 1;
   ```

4. **Check backend logs**
   - Look for exception messages (Groq API error? Network timeout?)

5. **Retry**
   - Click **Write a new version** to retry generation
   - Sometimes transient network issues cause failure

### Common errors

| Error | Fix |
|-------|-----|
| `Groq 429` (rate limit) | Wait 30 seconds, retry. Your API key hit the 8K TPM limit. |
| `Playwright timeout` | Network slow or competitor site down. Reduce competitor count. |
| `"No competitors found"` | Market may be too niche. Add more context to the 6 questions. |
| `Database locked` | Another memo is generating. Wait 2 minutes and retry. |

---

## Workflow 11: Run Locally Without Docker

### Prerequisites
- Python 3.12+
- Node 18+
- PostgreSQL 13+
- Redis

### Setup

```bash
# Backend
cd Backend
pip install -r requirements.txt
alembic upgrade head  # create schema
uvicorn main:app --reload

# Frontend (new terminal)
cd Frontend
npm install
npm run dev

# Celery worker (new terminal, if using background tasks)
cd Backend
celery -A celery_app worker --loglevel=info

# Redis (new terminal)
redis-server
```

### Access
- Frontend: `http://localhost:5173`
- API: `http://localhost:8000` (or `http://localhost:8000/docs` for OpenAPI)

---

## Need Help?

- **FAQ**: See README.md Troubleshooting section
- **API docs**: `http://localhost:8000/docs` (Swagger UI)
- **Code walkthrough**: Read `Backend/FLOW.md`
- **Screenshots**: See `docs/SCREENSHOTS.md`
