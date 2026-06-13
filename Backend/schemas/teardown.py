from pydantic import BaseModel, Field


class CompetitorItem(BaseModel):
    name: str = Field(..., description="Competitor name")
    why_competes: str = Field(..., description="Why this competitor is relevant")


class ProductTeardown(BaseModel):
    product_name: str = Field(..., description="Product name")

    one_liner: str = Field(..., description="Very short product summary")

    executive_summary: str = Field(..., description="High-level teardown summary")

    target_users: list[str] = Field(default_factory=list)

    pain_points: list[str] = Field(default_factory=list)

    core_features: list[str] = Field(default_factory=list)

    user_journey: list[str] = Field(default_factory=list)

    competitors: list[CompetitorItem] = Field(default_factory=list)

    market_positioning: str = Field(..., description="Where the product sits in the market")

    business_model: str = Field(..., description="Likely monetization model")

    moats: list[str] = Field(default_factory=list)

    opportunities: list[str] = Field(default_factory=list)

    risks: list[str] = Field(default_factory=list)

    verdict: str = Field(..., description="Final judgment")