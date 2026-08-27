"""
FastAPI application factory.
Mounts /v1 router; CORS enabled for frontend dev server.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.api.v1 import router as v1_router
from app.db.session import SessionLocal
from app.services.index_engine.runner import run_full_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _scheduled_pipeline_job():
    """APScheduler job — runs every 6 hours to recompute the index."""
    logger.info("Scheduled index pipeline starting...")
    db = SessionLocal()
    try:
        run_full_pipeline(db)
        logger.info("Scheduled index pipeline complete")
    except Exception as e:
        logger.error("Scheduled pipeline error: %s", e)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on startup; shut it down cleanly on exit."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _scheduled_pipeline_job,
        trigger="interval",
        hours=6,
        id="index_pipeline",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started — index pipeline will run every 6 hours")
    yield
    scheduler.shutdown(wait=False)
    logger.info("APScheduler shut down")


app = FastAPI(
    title="Real-Time Airfare Price Index API",
    description=(
        "SIH26056 — Team Runtime Rulers. "
        "Laspeyres chain-linked weighted national airfare index for India. "
        "Methodology: DEVELOPMENT.md §3."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/")
def root():
    return {
        "service": "Real-Time Airfare Price Index API",
        "team": "Runtime Rulers",
        "problem": "SIH26056",
        "docs": "/docs",
        "health": "/v1/health",
    }
