from pydantic import BaseModel, Field


class CompetitorSentiment(BaseModel):
    name: str = Field(..., description="Competitor product name")
    what_users_use: str = Field(
        ...,
        description="How customers currently use this product and in what context",
    )
    satisfaction_summary: str = Field(
        ...,
        description="high, mixed, low, or unknown — with brief evidence from reviews/search",
    )
    common_complaints: list[str] = Field(
        default_factory=list,
        description="Specific complaints or pain points users report about this competitor",
    )


class MarketGap(BaseModel):
    gap: str = Field(..., description="Unmet need or frustration in the market")
    evidence: str = Field(
        ...,
        description="Evidence grounded in user complaints or review data",
    )
    product_opportunity: str = Field(
        ...,
        description="How the founder's product idea can address this gap",
    )


class CustomerVoiceAnalysis(BaseModel):
    current_solutions: list[str] = Field(
        default_factory=list,
        description="What most customers currently use to solve this problem",
    )
    competitor_sentiment: list[CompetitorSentiment] = Field(default_factory=list)
    market_gaps: list[MarketGap] = Field(default_factory=list)
    recommended_features: list[str] = Field(
        default_factory=list,
        description="Product features that directly close identified market gaps",
    )


class CompetitorItem(BaseModel):
    name: str = Field(..., description="Competitor name (e.g. 'Pramp')")
    why_competes: str = Field(..., description="Full sentence explaining why this competitor is relevant to the product being analyzed")
    website: str = Field(
        default="",
        description="Company domain for logo display, e.g. 'stripe.com' — leave empty if unknown",
    )


class ProductTeardownLLMOutput(BaseModel):
    """Schema for LLM structured output — excludes customer_voice (attached from pipeline)."""

    product_name: str = Field(..., description="Crisp, memorable product name derived from the idea")

    one_liner: str = Field(..., description="One punchy sentence that captures what the product does and who it's for")

    executive_summary: str = Field(..., description="Write 2-3 detailed paragraphs covering: the problem, the product solution, target market, competitive angle, and business opportunity. This is the most important section.")

    target_users: list[str] = Field(default_factory=list, description="Array of 3-5 specific user segments.")

    pain_points: list[str] = Field(default_factory=list, description="Array of 3-5 distinct pain points grounded in customer voice evidence when available.")

    core_features: list[str] = Field(default_factory=list, description="Array of 3-5 gap-driven features aligned with recommended_features from Customer Voice input.")

    user_journey: list[str] = Field(default_factory=list, description="Array of 5-7 user journey steps in chronological order.")

    competitors: list[CompetitorItem] = Field(default_factory=list, description="Array of 3-5 competitor objects with name and why_competes.")

    market_positioning: str = Field(..., description="One thorough paragraph on market positioning and differentiation.")

    business_model: str = Field(..., description="One thorough paragraph on pricing, willingness to pay, and scalability.")

    moats: list[str] = Field(default_factory=list, description="Array of 2-4 competitive moats.")

    opportunities: list[str] = Field(default_factory=list, description="Array of 2-4 growth opportunities from underserved needs in Customer Voice.")

    risks: list[str] = Field(default_factory=list, description="Array of 2-4 distinct risks.")

    verdict: str = Field(..., description="Write 1-2 paragraphs with clear reasoning and final judgment.")


class ProductTeardown(ProductTeardownLLMOutput):
    customer_voice: CustomerVoiceAnalysis = Field(
        default_factory=CustomerVoiceAnalysis,
        description="Customer voice and gap analysis from market research; populated from pipeline evidence",
    )