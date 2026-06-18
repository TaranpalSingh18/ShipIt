from pydantic import BaseModel, Field


class CompetitorItem(BaseModel):
    name: str = Field(..., description="Competitor name (e.g. 'Pramp')")
    why_competes: str = Field(..., description="Full sentence explaining why this competitor is relevant to the product being analyzed")


class ProductTeardown(BaseModel):
    product_name: str = Field(..., description="Crisp, memorable product name derived from the idea")

    one_liner: str = Field(..., description="One punchy sentence that captures what the product does and who it's for")

    executive_summary: str = Field(..., description="Write 2-3 detailed paragraphs covering: the problem, the product solution, target market, competitive angle, and business opportunity. This is the most important section.")

    target_users: list[str] = Field(default_factory=list, description="Array of 3-5 specific user segments. Each item must be a descriptive sentence with context (e.g. 'Final-year engineering students in India preparing for campus placements who lack access to structured interview practice'). Do NOT combine multiple segments into one string.")

    pain_points: list[str] = Field(default_factory=list, description="Array of 3-5 distinct pain points. Each item must be a full sentence describing the problem and its real-world consequence. Do NOT combine multiple pain points into one string.")

    core_features: list[str] = Field(default_factory=list, description="Array of 3-5 distinct features. Each item must be a full sentence describing what the feature does and why it matters to the user. Do NOT combine multiple features into one string.")

    user_journey: list[str] = Field(default_factory=list, description="Array of 5-7 steps describing the user journey from discovery to ongoing usage. Each item must be a full sentence describing one concrete step in chronological order. Do NOT combine multiple steps into one string.")

    competitors: list[CompetitorItem] = Field(default_factory=list, description="Array of 3-5 competitor objects. Each object must have 'name' (string) and 'why_competes' (full sentence explaining the competitive dynamic). Do NOT put competitors as plain strings.")

    market_positioning: str = Field(..., description="One thorough paragraph (3-5 sentences) explaining where the product fits in the market landscape, how it differentiates from alternatives, and what specific niche it owns")

    business_model: str = Field(..., description="One thorough paragraph (3-5 sentences) explaining how the product makes money: pricing model, target customer willingness to pay, unit economics, and scalability")

    moats: list[str] = Field(default_factory=list, description="Array of 2-4 distinct competitive moats. Each item must be a detailed sentence or short paragraph explaining the defensible advantage. Do NOT combine multiple moats into one string.")

    opportunities: list[str] = Field(default_factory=list, description="Array of 2-4 distinct growth opportunities. Each item must be a full sentence with reasoning on why it's viable. Do NOT combine multiple opportunities into one string.")

    risks: list[str] = Field(default_factory=list, description="Array of 2-4 distinct risks. Each item must be a full sentence describing the risk and its potential impact. Do NOT combine multiple risks into one string.")

    verdict: str = Field(..., description="Write 1-2 paragraphs with clear reasoning. First paragraph summarizes the product opportunity and key strengths. Second paragraph covers critical risks and makes a final judgment.")
