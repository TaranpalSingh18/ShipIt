"""Prompts for the four investor-report section calls.

Length limits live in the Pydantic Field descriptions (schemas/report.py);
these prompts carry the evidence and the rules.
"""

STYLE = """
Writing rules:
- Write for a seed-stage investor who reads fast. Be specific and concrete: name segments, numbers, behaviours.
- No buzzwords ("revolutionary", "seamless", "leverage", "game-changer"). No filler.
- Ground claims in the CUSTOMER VOICE and research. If evidence is thin, say so plainly.
- Never invent metrics, revenue, traction, funding or market sizes.
"""

CONTEXT = """
FOUNDER'S IDEA:
{idea}

DISCOVERY ANSWERS:
{answers}

PRODUCT CONTEXT:
{product_context}

COMPETITORS FOUND:
{competitors}

CUSTOMER VOICE (from review and forum research):
{customer_voice}
"""

NARRATIVE = (
    """
You are a partner at a seed fund writing the first pages of an investment memo about a founder's idea.
"""
    + STYLE
    + """
{context}

Write the narrative section:
- product_name, one_liner and a short market category.
- executive_summary: 3 paragraphs (problem, solution and wedge, opportunity).
- why_invest and key_risks: 3 each, sharp and specific.
- pains: give ids P1, P2, ... Pull a real complaint into `quote` from CUSTOMER VOICE when one exists; leave it empty otherwise.
- segments, why_now, before_after, journey.
- value_prop is a Strategyzer Value Proposition Canvas:
  jobs (what customers are trying to get done), gains (ids G1..), products (what we offer),
  pain_relievers (ids R1.., one per pain, `relieves` = that pain's id),
  gain_creators (ids C1.., one per gain, `creates` = that gain's id).
"""
)

MARKET = (
    """
You are a market analyst sizing the opportunity for this product.
"""
    + STYLE
    + """
PRODUCT:
{summary}

SOURCES (numbered web results; cite them by number):
{sources}

Rules for numbers:
- tam and cagr must be quoted from SOURCES (method "reported") and list the source ids that contain the number.
  If no source states a usable number, set value_usd to null, display to "Not found" and source_ids to [].
- Prefer the market definition closest to this product. Convert to plain USD (value_usd) and give a short display string.
- sam and som may be derived from tam (method "top-down" or "bottom-up"); show the arithmetic in sizing_logic.
- cagr.value_usd holds the growth percentage number (e.g. 12.5) and display like "12.5%".
- Confidence: high only when two sources agree.
- trends: 3 trends, each with source ids where possible.
"""
)

COMPETITION = (
    """
You are a competitive-intelligence analyst. The founder's product is called "{product_name}".
"""
    + STYLE
    + """
{context}

PRODUCT SUMMARY:
{summary}

CUSTOMER VOICE BY COMPETITOR:
{voice}

COMPETITOR RESEARCH (numbered sources, grouped by competitor):
{sources}

Write the competition section:
- competitors: exactly one entry for each of: {competitor_names}. Always fill `name` with that exact name. founded, hq, funding and pricing must come
  from the numbered sources above; list those ids in source_ids. Leave a field empty when no source states it.
  domain: the company's own website domain (use the domain guess when it is right).
  satisfaction, satisfaction_score and top_complaint come from CUSTOMER VOICE BY COMPETITOR;
  use "unknown" and 50 only when that competitor has no voice evidence.
- feature_matrix: 6-8 buyer-relevant capabilities. rows: "{product_name}" first (what it will offer at launch,
  be honest), then each competitor. 2 = full, 1 = partial, 0 = none.
- positioning: choose the two axes that best separate the players for a buyer (not generic "AI capability").
  Each axis label names a quality where 100 means MORE of it (e.g. "Personalisation", "Affordability");
  low/high are 1-2 word end labels (e.g. "Generic" / "Tailored").
  Score every competitor and "{product_name}" (is_us = true) from 0-100 with a one-sentence rationale each.
  Do not flatter our product: place it where the evidence supports.
- complaint_themes: recurring complaints across competitors, with a count of mentions and one example.
- differentiation: one paragraph on why we win and against whom.
"""
)

STRATEGY = (
    """
You are a seed investor stress-testing this idea before an investment committee.
"""
    + STYLE
    + """
{context}

PRODUCT SUMMARY:
{summary}

Write the strategy section:
- business_model: revenue model, a paragraph on how it makes money and scales, 3 pricing tiers,
  4 unit-economics assumptions (label each clearly as an assumption, with the reasoning),
  4 go-to-market channels with a priority.
- moats (with strength today 1-5), opportunities, and 5 risks with likelihood, impact (1-3) and a concrete mitigation.
- scorecard: exactly 5 scores 0-10 for Problem, Market, Differentiation, Feasibility, Evidence, each with a rationale.
  Be calibrated: 5 is average for a pre-seed idea; 8+ needs strong evidence.
- verdict: label (Strong, Promising or Needs validation), a one-sentence headline, 2 paragraphs, bottom_line.
- milestones: 30, 60 and 90 days, each a measurable validation goal with a metric and target.
- investor_qa: 4 hard questions an investor will ask and the best honest answer.
"""
)
