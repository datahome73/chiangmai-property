from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.property import DistrictResponse
from app.services.property_service import get_districts

router = APIRouter(prefix="/districts", tags=["区域"])


@router.get("", response_model=List[DistrictResponse])
async def list_districts(
    db: AsyncSession = Depends(get_db),
):
    """获取所有区域统计"""
    results = await get_districts(db)
    return results
