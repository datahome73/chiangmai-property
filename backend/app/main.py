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


# ── Seed 数据接口 (仅开发/管理用) ──
@app.post("/api/v1/seed")
async def seed_data():
    """注入50条演示房源数据"""
    try:
        import random
        from datetime import datetime, timedelta
        from app.core.database import async_session_factory
        from app.models.property import Property, PriceHistory, User, PriceType, PropertyType

        DISTRICTS = [
            ("古城", 18.7883, 98.9853), ("宁曼路", 18.8000, 98.9680),
            ("长康路", 18.7800, 98.9980), ("杭东", 18.6870, 98.9190),
            ("讪赛", 18.8500, 99.0500), ("湄林", 18.9000, 98.9500),
            ("山甘烹", 18.7400, 99.1200), ("沙拉丕", 18.7000, 99.0100),
            ("东岸", 18.8200, 99.0200), ("清迈大学附近", 18.8050, 98.9550),
        ]
        NAMES = ["Supalai Monte", "The Astra Condo", "D Condo Sign",
                 "Punna Oasis", "Hillside Plaza", "Burasiri San Sai",
                 "The Shine Nimman", "The Unique Condo", "Punna Garden",
                 "Baan Kachana", "The Spring Condo", "My Hip Condo"]
        RENTS = [5000, 8000, 10000, 12000, 15000, 18000, 22000, 28000, 35000, 45000]
        SALES = [1500000, 2000000, 2800000, 3500000, 4500000, 5500000, 7000000, 8900000, 12000000, 18000000]
        SQM = [25, 30, 35, 40, 45, 50, 60, 75, 90, 110, 140, 180]
        TYPES = [PropertyType.CONDO, PropertyType.CONDO, PropertyType.HOUSE,
                 PropertyType.TOWNHOUSE, PropertyType.APARTMENT, PropertyType.CONDO]

        async with async_session_factory() as db:
            # 清空
            for table in [PriceHistory, Property]:
                await db.execute(table.__table__.delete())

            for i in range(50):
                d_name, lat, lng = random.choice(DISTRICTS)
                is_rent = random.random() > 0.35
                beds = random.choice([1, 1, 2, 2, 2, 3, 3, 4])
                baths = min(beds + random.choice([0, 1, 1]), 5)
                area = random.choice(SQM)
                prop = Property(
                    title=f"{d_name} — {random.choice(NAMES)}",
                    description=f"{beds}卧{baths}卫 {area}㎡ 位于{d_name}",
                    price_rent=random.choice(RENTS) if is_rent else None,
                    price_sale=random.choice(SALES) if not is_rent else None,
                    currency="THB",
                    price_type=PriceType.RENT if is_rent else PriceType.SALE,
                    bedrooms=beds, bathrooms=baths, area_sqm=area,
                    floor=random.randint(1, 15), total_floors=random.randint(5, 18),
                    furnished=random.random() > 0.2,
                    property_type=random.choice(TYPES),
                    address=f"{d_name}区，清迈", district=d_name,
                    sub_district=random.choice(["Pa Tan", "Suthep", "Chang Phueak", "Hai Ya"]),
                    lat=lat + (random.random() - 0.5) * 0.03,
                    lng=lng + (random.random() - 0.5) * 0.03,
                    source=random.choice(["ddproperty", "hipflat", "fazwaz"]),
                    source_url=f"https://example.com/{i}",
                    source_id=f"seed_{i}",
                    images=[f"https://picsum.photos/seed/cm{i}{ch}/800/500" for ch in ['a', 'b']],
                    is_active=True,
                    posted_date=datetime.utcnow() - timedelta(days=random.randint(0, 60)),
                )
                db.add(prop)
            await db.commit()

        return {"status": "ok", "message": "注入50条种子数据完成"}
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


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
