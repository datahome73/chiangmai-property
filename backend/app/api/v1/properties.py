from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.schemas.property import (
    PropertyResponse,
    PropertyListResponse,
    PropertyFilterParams,
    MarkerResponse,
    DistrictResponse,
    PriceHistoryResponse,
    AIAnalysisResponse,
    CompareAnalysisResponse,
    SmartSearchResponse,
)
from app.services.property_service import (
    get_properties,
    get_property_detail,
    get_properties_for_compare,
    get_markers,
    get_districts,
    get_price_history,
)
from app.services.ai_analysis_service import (
    analyze_property,
    compare_analysis,
    smart_search,
)

router = APIRouter(prefix="/properties", tags=["房产"])


@router.get("/compare", response_model=List[PropertyResponse])
async def compare_properties(
    ids: str = Query(..., description="逗号分隔的房产ID列表，如 1,2,3"),
    db: AsyncSession = Depends(get_db),
):
    """批量比价数据"""
    try:
        property_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的ID格式，请使用逗号分隔的数字")

    if not property_ids:
        raise HTTPException(status_code=400, detail="请至少提供一个房产ID")

    results = await get_properties_for_compare(db, property_ids)
    return [PropertyResponse.model_validate(p) for p in results]


@router.get("", response_model=PropertyListResponse)
async def list_properties(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    price_type: Optional[str] = Query(None, description="价格类型: rent/sale"),
    property_type: Optional[str] = Query(None, description="房产类型: condo/house/townhouse/apartment"),
    district: Optional[str] = Query(None, description="区域筛选"),
    min_price: Optional[float] = Query(None, description="最低价格"),
    max_price: Optional[float] = Query(None, description="最高价格"),
    bedrooms: Optional[int] = Query(None, description="卧室数量"),
    sort_by: str = Query("default", description="排序方式: default/price_asc/price_desc/newest"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """搜索房产列表"""
    filters = PropertyFilterParams(
        keyword=keyword,
        price_type=price_type,
        property_type=property_type,
        district=district,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    total, items = await get_properties(db, filters)
    return PropertyListResponse(
        total=total,
        items=[PropertyResponse.model_validate(p) for p in items],
    )


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取房产详情"""
    result = await get_property_detail(db, property_id)
    if not result:
        raise HTTPException(status_code=404, detail="房产未找到")
    return PropertyResponse.model_validate(result)


@router.get("/{property_id}/price-history", response_model=List[PriceHistoryResponse])
async def property_price_history(
    property_id: int,
    limit: int = Query(10, ge=1, le=100, description="返回条数"),
    db: AsyncSession = Depends(get_db),
):
    """获取房产价格变动历史"""
    records = await get_price_history(db, property_id, limit)
    return [PriceHistoryResponse.model_validate(r) for r in records]


# ============================================================
# AI 分析接口
# ============================================================

@router.get("/{property_id}/ai-analysis", response_model=AIAnalysisResponse)
async def property_ai_analysis(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """AI 房源分析 — 价格评估、评分、趋势、一句话总结"""
    result = await analyze_property(db, property_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return AIAnalysisResponse(**result)


@router.get("/ai/compare", response_model=CompareAnalysisResponse)
async def ai_compare_properties(
    ids: str = Query(..., description="逗号分隔的房产ID列表"),
    db: AsyncSession = Depends(get_db),
):
    """AI 比价智能推荐 — 多维度打分排序"""
    try:
        property_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的ID格式")

    if not property_ids:
        raise HTTPException(status_code=400, detail="请至少提供一个房产ID")

    result = await compare_analysis(db, property_ids)
    return CompareAnalysisResponse(**result)


@router.get("/ai/smart-search", response_model=SmartSearchResponse)
async def ai_smart_search(
    q: str = Query(..., description="自然语言搜索，如：'清迈大学附近两室月租1万以下'"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """AI 智能搜索 — 自然语言→结构化查询"""
    result = await smart_search(db, q, page=page, page_size=page_size)
    return SmartSearchResponse(**result)
