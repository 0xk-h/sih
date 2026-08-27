from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.index_engine.runner import run_full_pipeline
from app.schemas import ScrapeTriggerOut
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["scrape"])


def _background_pipeline(db_url: str):
    """Run the full pipeline in background. Creates its own DB session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        run_full_pipeline(db)
        logger.info("Background pipeline completed")
    except Exception as e:
        logger.error("Background pipeline failed: %s", e)
    finally:
        db.close()


@router.post("/scrape/trigger", response_model=ScrapeTriggerOut)
def trigger_scrape(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Manually trigger a scrape batch + index recomputation.
    POST /v1/scrape/trigger
    Used as demo control for live hackathon presentation.
    """
    batch_id = str(uuid.uuid4())
    logger.info("Scrape/index batch triggered manually: %s", batch_id)

    from app.config import settings
    background_tasks.add_task(_background_pipeline, settings.DATABASE_URL)

    return ScrapeTriggerOut(
        batch_id=batch_id,
        status="accepted",
        message=(
            "Index recomputation started in background. "
            "Check GET /v1/index/national in ~5 seconds."
        ),
    )
