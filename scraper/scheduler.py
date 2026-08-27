"""
APScheduler-based scraper scheduler.
Triggers fare collection from all configured sources per route × DTD bucket.
Runs every 6 hours in the background.
"""
import logging
import sys
import os
from datetime import date, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from scraper.sources.amadeus import get_amadeus_client
from scraper.loader import load_observations

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Routes to scrape (origin, destination, route_id resolved at runtime)
ROUTE_PAIRS = [
    ("DEL", "BOM"),
    ("DEL", "BLR"),
    ("BOM", "BLR"),
    ("DEL", "HYD"),
    ("DEL", "CCU"),
    ("BOM", "GOI"),
]

# MVP: only 2 DTD buckets
DTD_BUCKETS = [14, 1]


def _get_db_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


def scrape_and_load_amadeus():
    """
    For each route × DTD bucket, fetch offers from Amadeus for departure
    date = today + dtd_bucket, then load into fare_observations.
    """
    logger.info("=== Amadeus scrape job starting ===")
    db = _get_db_session()
    client = get_amadeus_client()
    today = date.today()

    try:
        # Resolve route_ids
        route_map: dict[str, int] = {}
        rows = db.execute(text("""
            SELECT r.route_id, o.iata_code || '-' || d.iata_code AS label
            FROM routes r
            JOIN airports o ON o.airport_id = r.origin_airport_id
            JOIN airports d ON d.airport_id = r.dest_airport_id
        """)).fetchall()
        route_map = {row.label: row.route_id for row in rows}

        total_loaded = 0
        for origin, dest in ROUTE_PAIRS:
            route_label = f"{origin}-{dest}"
            route_id = route_map.get(route_label)
            if not route_id:
                logger.warning("Route %s not found in DB, skipping", route_label)
                continue

            for dtd in DTD_BUCKETS:
                departure_date = today + timedelta(days=dtd)
                logger.info("Fetching Amadeus: %s DTD=%d dep=%s", route_label, dtd, departure_date)

                offers = client.get_flight_offers(origin, dest, departure_date)
                if not offers:
                    logger.info("No offers returned for %s DTD=%d", route_label, dtd)
                    continue

                # Attach route_id and dtd_bucket to each offer
                for offer in offers:
                    offer["route_id"] = route_id
                    offer["dtd_bucket"] = dtd

                n = load_observations(db, offers)
                total_loaded += n
                logger.info("  Loaded %d fares for %s DTD=%d", n, route_label, dtd)

        logger.info("=== Amadeus scrape complete: %d total fares loaded ===", total_loaded)

        # Trigger index recomputation
        from app.services.index_engine.runner import run_full_pipeline
        run_full_pipeline(db)
        logger.info("=== Index recomputation complete ===")

    except Exception as e:
        logger.error("Scrape job failed: %s", e)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    # Run immediately on start, then every 6 hours
    scheduler.add_job(scrape_and_load_amadeus, trigger="interval", hours=6, id="amadeus_scrape")
    scheduler.add_job(scrape_and_load_amadeus, trigger="date", id="amadeus_scrape_immediate")
    logger.info("Scheduler starting — Amadeus scrape will run every 6 hours")
    scheduler.start()
