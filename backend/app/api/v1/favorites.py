from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.favorite import FavoriteCreate, FavoriteResponse
from app.services.favorite_service import get_user_favorites, add_favorite, remove_favorite
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/favorites", tags=["收藏"])
auth_scheme = HTTPBearer()


async def _require_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
) -> int:
    """提取当前登录用户ID"""
    user_id = get_current_user(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的认证凭证")
    return user_id


@router.get("", response_model=List[FavoriteResponse])
async def list_favorites(
    user_id: int = Depends(_require_user),
    db: AsyncSession = Depends(get_db),
):
    """获取收藏列表（需认证）"""
    results = await get_user_favorites(db, user_id)
    return results


@router.post("", response_model=FavoriteResponse)
async def create_favorite(
    data: FavoriteCreate,
    user_id: int = Depends(_require_user),
    db: AsyncSession = Depends(get_db),
):
    """添加收藏"""
    result = await add_favorite(db, user_id, data.property_id)
    if not result:
        raise HTTPException(status_code=400, detail="收藏失败，可能已存在")
    return result


@router.delete("/{property_id}")
async def delete_favorite(
    property_id: int,
    user_id: int = Depends(_require_user),
    db: AsyncSession = Depends(get_db),
):
    """删除收藏"""
    success = await remove_favorite(db, user_id, property_id)
    if not success:
        raise HTTPException(status_code=404, detail="收藏未找到")
    return {"message": "收藏已删除"}
