# ShipIt Visual & Feature Guide

Quick reference for what each page of the investor memo shows and how to use the app.

## The App Flow

### 1. Sign Up / Login
Create an account with your email and password (Argon2 hashed, secure).

### 2. Create a Case
Name your product idea and write a brief description.

### 3. Answer 6 Questions
The app guides you through:
1. **Who is for** — Target customer segment
2. **The pain** — The core problem they face
3. **How often** — Frequency of the pain
4. **What they use now** — Current solutions
5. **Why this is better** — Your competitive advantage
6. **What you've checked** — Validation evidence

The form uses progressive disclosure—answer what you know, and targeted follow-ups appear for missing pieces.

### 4. Watch the Research
- **Competitors discovered** — Tavily searches find 5–8 real competitors
- **Market data collected** — TAM, CAGR, pricing, funding, founding dates
- **Logos & screenshots captured** — Playwright grabs competitor homepages
- **Customer voice analyzed** — Sentiment from reviews, forums, complaints

A live progress bar shows: Research (8%) → Competitors (30%) → Market & Writing (75%) → PDF (90%) → Done (100%)

### 5. Read the Memo

The memo is available as:
- **PDF** — Download and share with investors, advisors, your team
- **Interactive web report** — Hover charts, sortable tables, sources drawer

---

## The 12-Page Memo

### Page 1: Executive One-Pager
**What:** Verdict (Strong / Promising / Needs validation), readiness score, 4 KPIs, summary, risks

**Why:** Investors skim this first. One page should tell them if they care enough to read more.

---

### Page 2: Problem & Customer
**What:** 3–4 pain cards with real user quotes, customer segments, willingness to pay, "why now" timeline

**Why:** Investors invest in solving urgent, expensive problems. Show them you understand the pain.

---

### Page 3: Solution & Value Proposition
**What:** Strategyzer canvas (fixed: pains ↔ relievers, gains ↔ creators), before/after, user journey

**Why:** Prove your product actually solves the stated pains. Show the before/after win.

---

### Page 4: Market Opportunity
**What:** TAM/SAM/SOM as concentric circles, CAGR, 3 market trends, sizing logic, confidence levels

**Why:** Investors need to know the market is big enough to be worth the effort.

---

### Page 5: Competitive Landscape
**What:** One card per competitor (logo, screenshot, founding year, HQ, funding, pricing, satisfaction, complaint)

**Why:** Investors want to know you've done your homework and understand where you fit.

---

### Page 6: Head-to-Head
**What:** Feature matrix (your product vs. competitors on 6–8 capabilities), positioning map with rationale

**Why:** Show you're not just iterating—you're differentiated on specific dimensions.

---

### Page 7: Voice of Customer
**What:** Sentiment bars per competitor, complaint theme frequency, gap → evidence → angle table

**Why:** Show that your features aren't invented—they solve real problems people complain about.

---

### Page 8: Business Model & GTM
**What:** Revenue model, pricing tiers vs. competitors, GTM channels with priority, unit economics

**Why:** Investors want to know you've thought through how to make money.

---

### Page 9: Risks & Moats
**What:** 3×3 likelihood × impact heatmap with mitigations per risk, moat strength assessment

**Why:** Investors want to know you've thought about what could go wrong and how you'd defend.

---

### Page 10: Verdict & Next Steps
**What:** Five-axis radar scorecard, full verdict statement, 30/60/90-day milestones, investor Q&A

**Why:** Wrap up with your recommendation and concrete next steps.

---

### Page 11: Sources
**What:** Numbered bibliography of every web page referenced in the memo

**Why:** Investors want to verify your claims. Every number in pages 1–10 links to a source.

---

## Interactive Report Features

### Sorting & Filtering
- **Competitor table** — Sort by funding, pricing, satisfaction
- **Features matrix** — Filter to show only your top features
- **Timeline** — Zoom in/out on 90-day milestones

### Hover Tooltips
- **Positioning map** — Hover a dot to see the competitor and the reasoning
- **Sentiment bars** — Hover to see source sample complaints
- **Risk heatmap** — Hover cells to see the mitigation strategy

### Sources Drawer
- Click any footnote number (e.g., `[31]`) to open the sources panel
- Panel shows all sources cited on that page
- Click a source URL to open it in a new tab

### PDF Download
- Button at the top of the report
- Downloads as `ProductName_MemoYear-Month-Day.pdf`
- Self-contained (all images embedded as base64, all fonts bundled)
- Ready to email or print

---

## Design Highlights

### Dark & Light Themes
- **Dark** (default): Navy background (#0a0e1f), indigo accent (#7c6cff), glass morphism surfaces
- **Light**: Off-white background (#f6f6fb), purple accent (#5546f0), clean surfaces
- Toggle with the moon/sun icon in the top bar
- Persists in localStorage across sessions

### Mobile Responsive
- 1440px desktop → 390px mobile, no horizontal scroll
- Report tables scroll horizontally inside cards
- TOC becomes a dropdown on mobile
- Charts resize to fit the viewport

### Typography
- **Display text**: Fraunces serif (elegant, high-contrast for headlines)
- **Body text**: Inter sans (readable, professional)
- Fonts are bundled in the PDF (₹, €, accented chars render correctly anywhere)

### Print Ready
- A4 page size with running header/footer
- Page numbers ("Page X of 12")
- Confidentiality notice at the bottom
- Color scheme optimized for both screen and print
