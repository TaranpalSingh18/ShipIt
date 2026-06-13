from pydantic import BaseModel
from typing import Optional

class ProductTeardown(BaseModel):
    product_name: str
    executive_summary: str
    target_users: list[str]
    pain_points: list[str]
    core_features: list[str]
    competitors: list[str]
    opportunities: list[str]
    risks: list[str]
    verdict: str