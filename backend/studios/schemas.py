from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StudioCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    phone: Optional[str] = Field(default=None, max_length=20)


class StudioOut(BaseModel):
    studio_id: int
    provider_id: Optional[int] = None
    name: str
    address: str
    description: Optional[str] = None
    phone: Optional[str] = None
    avg_rating: Optional[float] = None
    review_count: int = 0


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    review_id: int
    studio_id: Optional[int] = None
    customer_id: Optional[int] = None
    rating: int
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
