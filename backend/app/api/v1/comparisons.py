from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.favorite import ComparisonCreate, ComparisonResponse
from app.services.favorite_service import get_user_comparisons, save_comparison, delete_comparison
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/comparisons", tags=["比价"])
auth_scheme = HTTPBearer()


async def _require_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
) -> int:
    """提取当前登录用户ID"""
    user_id = get_current_user(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的认证凭证")
    return user_id


@router.get("", response_model=List[ComparisonResponse])
async def list_comparisons(
    user_id: int = Depends(_require_user),
    db: AsyncSession = Depends(get_db),
):
    """获取比价列表（需认证）"""
    results = await get_user_comparisons(db, user_id)
    return results


@router.post("", response_model=ComparisonResponse)
async def create_comparison(
    data: ComparisonCreate,
    user_id: int = Depends(_require_user),
    db: AsyncSession = Depends(get_db),
):
    """保存比价"""
    result = await save_comparison(db, user_id, data.name, data.property_ids)
    if not result:
        raise HTTPException(status_code=400, detail="保存比价失败")
    return result


@router.delete("/{comparison_id}")
async def remove_comparison(
    comparison_id: int,
    user_id: int = Depends(_require_user),
    db: AsyncSession = Depends(get_db),
):
    """删除比价"""
    success = await delete_comparison(db, user_id, comparison_id)
    if not success:
        raise HTTPException(status_code=404, detail="比价未找到")
    return {"message": "比价已删除"}
