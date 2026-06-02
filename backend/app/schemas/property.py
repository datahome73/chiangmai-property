from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PriceTypeEnum(str, Enum):
    RENT = "rent"
    SALE = "sale"
    BOTH = "both"


class PropertyTypeEnum(str, Enum):
    CONDO = "condo"
    HOUSE = "house"
    TOWNHOUSE = "townhouse"
    APARTMENT = "apartment"
    OTHER = "other"


class PropertyResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price_rent: Optional[float] = None
    price_sale: Optional[float] = None
    currency: str = "THB"
    price_type: PriceTypeEnum
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    furnished: Optional[bool] = None
    property_type: PropertyTypeEnum
    address: Optional[str] = None
    district: Optional[str] = None
    sub_district: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    source: str
    source_url: Optional[str] = None
    images: Optional[List[str]] = None
    is_active: bool = True
    posted_date: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    price_per_sqm: Optional[float] = None  # 计算字段

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    total: int
    items: List[PropertyResponse]


class PropertyFilterParams(BaseModel):
    keyword: Optional[str] = None
    price_type: Optional[PriceTypeEnum] = None
    property_type: Optional[PropertyTypeEnum] = None
    district: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    sort_by: Optional[str] = None  # price_asc, price_desc, newest
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class MarkerResponse(BaseModel):
    id: int
    lat: Optional[float] = None
    lng: Optional[float] = None
    price_rent: Optional[float] = None
    price_sale: Optional[float] = None
    price_type: PriceTypeEnum

    class Config:
        from_attributes = True


class DistrictResponse(BaseModel):
    name: str
    name_en: Optional[str] = Field(None, alias="name_en")
    count: int
    avg_price_rent: Optional[float] = None
    avg_price_sale: Optional[float] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class PriceHistoryResponse(BaseModel):
    id: int
    property_id: int
    price_rent: Optional[float] = None
    price_sale: Optional[float] = None
    currency: str = "THB"
    price_type: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True

class CompareRequest(BaseModel):
    ids: List[int] = Field(..., min_length=1, max_length=20)


class CompareResponse(BaseModel):
    items: List[PropertyResponse]
