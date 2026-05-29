from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.models import *  # noqa: F401, F403
from app.api.v1.properties import router as properties_router
from app.api.v1.markers import router as markers_router
from app.api.v1.districts import router as districts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.comparisons import router as comparisons_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="清迈房产比价平台 API",
    description="Chiang Mai Property Comparison Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(properties_router, prefix="/api/v1")
app.include_router(markers_router, prefix="/api/v1")
app.include_router(districts_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(favorites_router, prefix="/api/v1")
app.include_router(comparisons_router, prefix="/api/v1")


@app.get("/api")
async def root():
    return {
        "message": "清迈房产比价平台 API",
        "version": "0.1.0",
        "env": settings.ENV,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.ENV}


# ─── Serve Frontend Static Files (Production) ─────────────
# In production, the built Vue app is served by FastAPI
frontend_dist = os.path.join(os.path.dirname(__file__), "../../frontend-react/dist")
if settings.ENV == "production" and os.path.isdir(frontend_dist):
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        """SPA fallback: serve index.html for any non-API route"""
        if not request.url.path.startswith("/api/"):
            index_path = os.path.join(frontend_dist, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
        raise exc
