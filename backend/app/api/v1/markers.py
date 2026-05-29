from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.schemas.property import MarkerResponse
from app.services.property_service import get_markers

router = APIRouter(prefix="/markers", tags=["地图"])


@router.get("", response_model=List[MarkerResponse])
async def list_markers(
    lat_min: Optional[float] = Query(None, description="纬度下限（西南角）"),
    lat_max: Optional[float] = Query(None, description="纬度上限（东北角）"),
    lng_min: Optional[float] = Query(None, description="经度下限（西南角）"),
    lng_max: Optional[float] = Query(None, description="经度上限（东北角）"),
    db: AsyncSession = Depends(get_db),
):
    """获取地图标注（可根据地图视口范围过滤）"""
    results = await get_markers(
        db,
        lat_min=lat_min,
        lat_max=lat_max,
        lng_min=lng_min,
        lng_max=lng_max,
    )
    return [MarkerResponse.model_validate(p) for p in results]
