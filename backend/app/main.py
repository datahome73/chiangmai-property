from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging

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
# In production, the built frontend is served by FastAPI
frontend_dist = os.path.join(os.path.dirname(__file__), "../../frontend-react/dist")
logger = logging.getLogger(__name__)
logger.info("frontend_dist path: %s exists=%s", os.path.abspath(frontend_dist), os.path.isdir(frontend_dist))
if settings.ENV == "production":
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    # Try multiple paths for Docker build compatibility
    dist_candidates = [
        frontend_dist,
        os.path.join(os.path.dirname(__file__), "../frontend-react/dist"),
        os.path.join(os.path.dirname(__file__), "../../../frontend-react/dist"),
        "/app/frontend-react/dist",
    ]
    resolved_dist = None
    for p in dist_candidates:
        ap = os.path.abspath(p)
        logger.info("trying dist path: %s exists=%s", ap, os.path.isdir(ap))
        if os.path.isdir(ap):
            resolved_dist = ap
            break

    if resolved_dist and os.path.isdir(resolved_dist):
        assets_dir = os.path.join(resolved_dist, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
            logger.info("mounted /assets from %s", assets_dir)

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            if full_path.startswith("api/") or full_path.startswith("assets/") or full_path == "health":
                raise HTTPException(status_code=404)
            index_path = os.path.join(resolved_dist, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            raise HTTPException(status_code=404)
    else:
        logger.warning("frontend dist not found, SPA serving disabled")
        # Health check endpoint
        @app.get("/debug-paths")
        async def debug_paths():
            import os as _os
            return {
                "cwd": _os.getcwd(),
                "dir__file__": _os.path.dirname(__file__),
                "candidates": {p: _os.path.isdir(_os.path.abspath(p)) for p in dist_candidates},
                "ls_backend": _os.listdir(_os.path.join(_os.path.dirname(__file__), "../..")),
            }
