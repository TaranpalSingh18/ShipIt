"""Investor report schema.

The report is written by four LLM section calls (see routes/report/generator.py).
Each `*Section` model below is the structured output of one call; `InvestorReport`
is the assembled document that the PDF template and the web report both read.

Every model has defaults so a partial LLM answer still validates. Numbers that
need evidence carry `source_ids`, which point into `InvestorReport.sources`.
"""

from pydantic import BaseModel, Field

from schemas.teardown import CustomerVoiceAnalysis


# ---------- shared ----------

class Source(BaseModel):
    id: int
    title: str = ""
    url: str = ""
    domain: str = ""


class Figure(BaseModel):
    label: str = Field("", description="What is measured, e.g. 'Global meal-kit market (2025)'")
    value_usd: float | None = Field(
        None,
        description="Value in plain US dollars (e.g. 4200000000 for $4.2B). For a growth rate, the percentage number (e.g. 12.5). null if no source supports it.",
    )
    display: str = Field("", description="Short human form, e.g. '$4.2B' or '12.5%'")
    method: str = Field("", description="'reported' (quoted from a source), 'top-down' or 'bottom-up'")
    source_ids: list[int] = Field(default_factory=list, description="Ids from the numbered SOURCES list that support this number")
    confidence: str = Field("low", description="high, medium or low")
    note: str = Field("", description="One sentence on how the number was derived")


# ---------- call A: narrative, problem, value proposition ----------

class Pain(BaseModel):
    id: str = Field("", description="P1, P2, ...")
    title: str = ""
    detail: str = Field("", description="Two sentences on the pain and who feels it")
    severity: int = Field(3, description="1 (mild) to 5 (hair on fire)")
    quote: str = Field("", description="A real user complaint from CUSTOMER VOICE, verbatim or close paraphrase. Empty if none.")
    quote_by: str = Field("", description="Where the quote comes from, e.g. 'Reddit user on Competitor X'")


class Segment(BaseModel):
    name: str = ""
    job_to_be_done: str = ""
    frequency: str = Field("", description="How often the problem occurs for this segment")
    current_solution: str = ""
    willingness_to_pay: str = Field("", description="low, medium or high, with a short reason")


class WhyNow(BaseModel):
    signal: str = Field("", description="Short label, e.g. 'LLM costs fell 10x'")
    detail: str = ""


class Gain(BaseModel):
    id: str = Field("", description="G1, G2, ...")
    text: str = ""


class Reliever(BaseModel):
    id: str = Field("", description="R1, R2, ...")
    text: str = ""
    relieves: str = Field("", description="Id of the pain this relieves, e.g. 'P1'")


class Creator(BaseModel):
    id: str = Field("", description="C1, C2, ...")
    text: str = ""
    creates: str = Field("", description="Id of the gain this creates, e.g. 'G1'")


class ValueProp(BaseModel):
    jobs: list[str] = Field(default_factory=list, description="3 customer jobs-to-be-done")
    gains: list[Gain] = Field(default_factory=list, description="3 gains the customer wants")
    products: list[str] = Field(default_factory=list, description="3 products/features we offer")
    pain_relievers: list[Reliever] = Field(default_factory=list, description="One reliever per pain")
    gain_creators: list[Creator] = Field(default_factory=list, description="One creator per gain")


class BeforeAfter(BaseModel):
    aspect: str = ""
    before: str = ""
    after: str = ""


class JourneyStep(BaseModel):
    title: str = ""
    detail: str = ""


class NarrativeSection(BaseModel):
    product_name: str = Field("", description="Crisp, memorable product name")
    one_liner: str = Field("", description="One sentence, max 22 words: what it does and for whom")
    category: str = Field("", description="Market category in 2-5 words, e.g. 'AI interview practice'")
    market_keywords: list[str] = Field(
        default_factory=list,
        description="2 established, broader market names that analyst reports size, e.g. 'online test preparation market', 'corporate e-learning market'",
    )
    executive_summary: list[str] = Field(default_factory=list, description="Exactly 3 paragraphs of 50-70 words: problem, solution, opportunity")
    why_invest: list[str] = Field(default_factory=list, description="3 reasons an investor should care, max 18 words each")
    key_risks: list[str] = Field(default_factory=list, description="3 biggest risks, max 18 words each")
    pains: list[Pain] = Field(default_factory=list, description="3-4 pains")
    segments: list[Segment] = Field(default_factory=list, description="2-4 customer segments")
    why_now: list[WhyNow] = Field(default_factory=list, description="3 reasons this is possible or urgent now")
    value_prop: ValueProp = Field(default_factory=ValueProp)
    before_after: list[BeforeAfter] = Field(default_factory=list, description="4 rows comparing life before and after the product")
    journey: list[JourneyStep] = Field(default_factory=list, description="5-6 steps of the user journey in order")


# ---------- call B: market ----------

class Trend(BaseModel):
    title: str = ""
    detail: str = ""
    source_ids: list[int] = Field(default_factory=list)


class MarketSection(BaseModel):
    tam: Figure = Field(default_factory=Figure, description="Total addressable market")
    sam: Figure = Field(default_factory=Figure, description="Serviceable addressable market")
    som: Figure = Field(default_factory=Figure, description="Serviceable obtainable market in 3-5 years")
    cagr: Figure = Field(default_factory=Figure, description="Annual market growth rate in percent")
    sizing_logic: list[str] = Field(default_factory=list, description="3-5 short steps showing how SAM and SOM follow from TAM")
    trends: list[Trend] = Field(default_factory=list, description="3 market trends with sources")


# ---------- call C: competition ----------

class Competitor(BaseModel):
    name: str = ""
    domain: str = Field("", description="Company website domain, e.g. 'notion.so'")
    tagline: str = Field("", description="What they sell, max 12 words")
    founded: str = Field("", description="Year founded, only if in SOURCES, else empty")
    hq: str = Field("", description="Headquarters city/country, only if in SOURCES, else empty")
    funding: str = Field("", description="Total funding raised, e.g. '$45M (Series B)', only if in SOURCES, else empty")
    pricing: str = Field("", description="Entry price, e.g. 'From $12/user/mo' or 'Free + $8/mo', only if in SOURCES, else empty")
    target_customer: str = ""
    strengths: list[str] = Field(default_factory=list, description="2 strengths")
    weaknesses: list[str] = Field(default_factory=list, description="2 weaknesses, grounded in complaints")
    satisfaction: str = Field("unknown", description="high, mixed, low or unknown")
    satisfaction_score: int = Field(50, description="0-100 estimate of user satisfaction from the voice evidence")
    top_complaint: str = ""
    threat: str = Field("medium", description="How much of a threat to us: high, medium or low")
    source_ids: list[int] = Field(default_factory=list, description="Ids from SOURCES supporting founded/hq/funding/pricing")
    # filled in by research, not by the LLM
    logo: str = ""
    screenshot: str = ""


class MatrixRow(BaseModel):
    name: str = ""
    scores: list[int] = Field(default_factory=list, description="One per capability: 2 = full, 1 = partial, 0 = none")


class FeatureMatrix(BaseModel):
    capabilities: list[str] = Field(default_factory=list, description="6-8 capabilities that matter to buyers")
    rows: list[MatrixRow] = Field(default_factory=list, description="Our product first, then each competitor")


class Axis(BaseModel):
    label: str = ""
    low: str = ""
    high: str = ""


class PositionPoint(BaseModel):
    name: str = ""
    x: int = Field(50, description="0-100")
    y: int = Field(50, description="0-100")
    rationale: str = Field("", description="One sentence explaining this placement")
    is_us: bool = False


class Positioning(BaseModel):
    x_axis: Axis = Field(default_factory=Axis)
    y_axis: Axis = Field(default_factory=Axis)
    points: list[PositionPoint] = Field(default_factory=list)


class ComplaintTheme(BaseModel):
    theme: str = ""
    mentions: int = Field(1, description="How many competitors / reviews show this theme")
    example: str = ""


class CompetitionSection(BaseModel):
    competitors: list[Competitor] = Field(default_factory=list)
    feature_matrix: FeatureMatrix = Field(default_factory=FeatureMatrix)
    positioning: Positioning = Field(default_factory=Positioning)
    complaint_themes: list[ComplaintTheme] = Field(default_factory=list, description="4-6 recurring complaint themes")
    differentiation: str = Field("", description="One paragraph: why we win")


# ---------- call D: strategy, risk, verdict ----------

class PricingTier(BaseModel):
    name: str = ""
    price: str = ""
    for_who: str = ""
    includes: list[str] = Field(default_factory=list)


class UnitMetric(BaseModel):
    metric: str = ""
    value: str = ""
    assumption: str = ""


class Channel(BaseModel):
    channel: str = ""
    tactic: str = ""
    priority: str = Field("secondary", description="primary, secondary or experimental")


class BusinessModel(BaseModel):
    revenue_model: str = Field("", description="e.g. 'B2B SaaS subscription'")
    summary: str = Field("", description="One paragraph on how the business makes money and scales")
    pricing_tiers: list[PricingTier] = Field(default_factory=list, description="3 proposed tiers")
    unit_economics: list[UnitMetric] = Field(default_factory=list, description="4 assumed metrics (CAC, ACV, gross margin, payback)")
    gtm: list[Channel] = Field(default_factory=list, description="4 go-to-market channels")


class Moat(BaseModel):
    name: str = ""
    detail: str = ""
    strength: int = Field(3, description="1-5 today")


class Opportunity(BaseModel):
    title: str = ""
    detail: str = ""


class Risk(BaseModel):
    risk: str = ""
    category: str = Field("", description="market, product, execution, regulatory or competition")
    likelihood: int = Field(2, description="1 low, 2 medium, 3 high")
    impact: int = Field(2, description="1 low, 2 medium, 3 high")
    mitigation: str = ""


class Score(BaseModel):
    dimension: str = ""
    score: int = Field(5, description="0-10")
    rationale: str = ""


class Verdict(BaseModel):
    label: str = Field("Needs validation", description="Strong, Promising or Needs validation")
    headline: str = Field("", description="One sentence judgement")
    paragraphs: list[str] = Field(default_factory=list, description="2 paragraphs of reasoning")
    bottom_line: str = ""


class Milestone(BaseModel):
    horizon: str = Field("", description="30 days, 60 days or 90 days")
    goal: str = ""
    metric: str = ""
    target: str = ""


class QA(BaseModel):
    question: str = ""
    answer: str = ""


class StrategySection(BaseModel):
    business_model: BusinessModel = Field(default_factory=BusinessModel)
    moats: list[Moat] = Field(default_factory=list, description="3 moats")
    opportunities: list[Opportunity] = Field(default_factory=list, description="3 growth opportunities")
    risks: list[Risk] = Field(default_factory=list, description="5 risks")
    scorecard: list[Score] = Field(
        default_factory=list,
        description="Exactly 5 scores in this order: Problem, Market, Differentiation, Feasibility, Evidence",
    )
    verdict: Verdict = Field(default_factory=Verdict)
    milestones: list[Milestone] = Field(default_factory=list, description="3 milestones: 30, 60, 90 days")
    investor_qa: list[QA] = Field(default_factory=list, description="4 hard questions an investor will ask, with suggested answers")


# ---------- assembled ----------

class ReportMeta(BaseModel):
    generated_at: str = ""
    idea: str = ""
    readiness: int = 0
    competitors_analysed: int = 0
    pain_signals: int = 0
    evidence: str = "low"


class InvestorReport(BaseModel):
    meta: ReportMeta = Field(default_factory=ReportMeta)
    narrative: NarrativeSection = Field(default_factory=NarrativeSection)
    market: MarketSection = Field(default_factory=MarketSection)
    competition: CompetitionSection = Field(default_factory=CompetitionSection)
    strategy: StrategySection = Field(default_factory=StrategySection)
    customer_voice: CustomerVoiceAnalysis = Field(default_factory=CustomerVoiceAnalysis)
    sources: list[Source] = Field(default_factory=list)
