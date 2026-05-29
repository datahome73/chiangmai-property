from typing import Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import secrets
from jose import jwt, JWTError

from app.models.property import User
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse
from app.core.config import settings


def _hash_password(password: str) -> str:
    """使用 PBKDF2-SHA256 哈希密码（不依赖 bcrypt）"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return f"{salt}${pwd_hash}"


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        salt, pwd_hash = hashed_password.split("$", 1)
        check = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return pwd_hash == check
    except (ValueError, AttributeError):
        return False


def create_token(user_id: int) -> str:
    """生成 JWT token。"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


def get_current_user(token: str) -> Optional[int]:
    """
    从 token 中解析用户 ID。
    返回 user_id 或 None（如果 token 无效/过期）。
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        return int(user_id_str)
    except JWTError:
        return None


async def register_user(
    db: AsyncSession,
    data: UserRegisterRequest,
) -> Optional[TokenResponse]:
    """
    注册用户。
    返回 TokenResponse（含用户信息和 token）或 None（如果手机号已存在）。
    """
    # Check if phone already exists
    if data.phone:
        existing = await db.execute(
            select(User).where(User.phone == data.phone)
        )
        if existing.scalar_one_or_none():
            return None

    # Create user
    user = User(
        phone=data.phone,
        nickname=data.nickname,
        password_hash=_hash_password(data.password),
        preferred_language="zh",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Generate token
    access_token = create_token(user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


async def authenticate_user(
    db: AsyncSession,
    phone: Optional[str],
    password: str,
) -> Optional[TokenResponse]:
    """
    验证用户登录。
    返回 TokenResponse 或 None（认证失败）。
    """
    if not phone:
        return None

    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        return None

    if not _verify_password(password, user.password_hash):
        return None

    # Generate token
    access_token = create_token(user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
