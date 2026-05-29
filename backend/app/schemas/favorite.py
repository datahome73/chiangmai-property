from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FavoriteCreate(BaseModel):
    property_id: int


class FavoriteResponse(BaseModel):
    id: int
    property_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ComparisonCreate(BaseModel):
    name: Optional[str] = None
    property_ids: List[int]


class ComparisonResponse(BaseModel):
    id: int
    name: Optional[str] = None
    property_ids: List[int]
    created_at: datetime

    class Config:
        from_attributes = True
