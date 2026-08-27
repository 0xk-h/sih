"""
Index Engine — Runner
Orchestrates the full pipeline: fare_observations → daily_route_price → index_values.
Callable both on-demand (from API) and via APScheduler.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
import logging

from app.services.index_engine.aggregator import aggregate_to_daily_route_price, DTD_BUCKETS
from app.services.index_engine.index_calc import compute_index

logger = logging.getLogger(__name__)


def run_full_pipeline(
    db: Session,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict:
    """
    Full end-to-end index computation:
    1. Aggregate fare_observations → daily_route_price for each DTD bucket
    2. Compute Laspeyres chain-linked index for each DTD bucket
    3. Return results keyed by dtd_bucket

    Called both on-demand via POST /v1/scrape/trigger and by the scheduler.
    """
    if to_date is None:
        to_date = date.today()
    if from_date is None:
        from_date = to_date - timedelta(days=90)

    logger.info(
        "Running full index pipeline: %s → %s for DTD buckets %s",
        from_date, to_date, DTD_BUCKETS
    )

    results = {}

    # Step 1: Aggregate fare_observations → daily_route_price (covers all DTD buckets)
    logger.info("Aggregating fare observations into daily route prices...")
    agg_df = aggregate_to_daily_route_price(db, from_date, to_date)
    if agg_df.empty:
        logger.warning("No fare observations found in date range %s to %s", from_date, to_date)

    # Step 2: Compute chain-linked Laspeyres index per DTD bucket
    for dtd in DTD_BUCKETS:
        logger.info("Computing Laspeyres index for DTD bucket %d", dtd)
        index_result = compute_index(db, dtd_bucket=dtd, from_date=from_date, to_date=to_date)
        results[dtd] = index_result

    national_counts = {dtd: len(res.get("national", [])) for dtd, res in results.items()}
    logger.info("Index pipeline complete. National series lengths: %s", national_counts)

    return results
