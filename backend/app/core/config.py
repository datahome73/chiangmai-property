from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Environment
    ENV: str = "development"  # development | production

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./cmproperty.db"
    DATABASE_URL_SYNC: str = "sqlite:///./cmproperty.db"

    # Redis (optional in dev)
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "changeme-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Proxy (for crawlers)
    PROXY_ENABLED: bool = False
    PROXY_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
