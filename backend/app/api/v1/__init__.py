from fastapi import APIRouter
from app.api.v1 import health, routes, fares, index, dashboard, scrape, data_quality

router = APIRouter(prefix="/v1")

router.include_router(health.router)
router.include_router(routes.router)
router.include_router(fares.router)
router.include_router(index.router)
router.include_router(dashboard.router)
router.include_router(scrape.router)
router.include_router(data_quality.router)
