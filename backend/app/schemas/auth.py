from pydantic import BaseModel, Field
from typing import Optional


class UserRegisterRequest(BaseModel):
    phone: Optional[str] = None
    password: str = Field(min_length=6)
    nickname: Optional[str] = None


class UserLoginRequest(BaseModel):
    phone: Optional[str] = None
    password: str


class UserResponse(BaseModel):
    id: int
    nickname: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: str = "zh"

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
