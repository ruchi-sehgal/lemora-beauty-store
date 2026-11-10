from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["skincare", "fragrance", "makeup", "haircare", "lifestyle"]
SkinType = Literal["oily", "dry", "sensitive", "combination", "mature", "normal", "all"]
Concern = Literal[
    "anti-aging", "hydration", "brightening", "pores & oil control", "soothing",
    "exfoliation", "sun protection", "barrier repair",
    "damage repair", "volume", "color protection", "shine", "scalp care",
]
Gender = Literal["feminine", "masculine", "unisex"]


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category | None = None
    brands: list[str] | None = None
    product_type: str | None = None
    skin_types: list[SkinType] | None = None
    concerns: list[Concern] | None = None
    gender: Gender | None = None
    max_price_sgd: Annotated[float, Field(gt=0, le=2000)] | None = None
    limit: Annotated[int, Field(ge=1, le=20)] = 10    
    exclude_skus: Annotated[list[str], Field(max_length=20)] | None = None
    exclude_brands: Annotated[list[str], Field(max_length=10)] | None = None

    


class Recommendation(BaseModel):
    sku_id: str
    reason: Annotated[str, Field(max_length=200)]


class AssistantReply(BaseModel):
    message: str
    recommendations: Annotated[list[Recommendation], Field(max_length=5)] = []
    follow_up_question: str | None = None