from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse
from app.services.auth_service import register_user, authenticate_user, get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])
auth_scheme = HTTPBearer()


async def _require_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
) -> int:
    """提取当前登录用户ID"""
    user_id = get_current_user(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的认证凭证")
    return user_id


@router.post("/register", response_model=TokenResponse)
async def register(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户注册"""
    result = await register_user(db, data)
    if not result:
        raise HTTPException(status_code=400, detail="注册失败，用户可能已存在")
    return result


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    result = await authenticate_user(db, data.phone, data.password)
    if not result:
        raise HTTPException(status_code=401, detail="手机号或密码错误")
    return result


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: int = Depends(_require_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户信息"""
    from sqlalchemy import select
    from app.models.property import User as UserModel
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户未找到")
    return UserResponse.model_validate(user)
