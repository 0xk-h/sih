"""
Scraper Loader — writes normalized fare data from scrapers into fare_observations.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def load_observations(db: Session, fares: list[dict], batch_id: uuid.UUID | None = None) -> int:
    """
    Insert normalized fare dicts into fare_observations.
    Applies dedup logic (ON CONFLICT DO NOTHING).

    Args:
        db: SQLAlchemy session
        fares: list of normalized fare dicts from any scraper source
        batch_id: optional batch UUID for audit trail

    Returns:
        count of rows actually inserted
    """
    if not fares:
        return 0

    if batch_id is None:
        batch_id = uuid.uuid4()

    # Resolve airline_id from iata_code
    airline_cache: dict[str, int | None] = {}

    def get_airline_id(iata: str | None) -> int | None:
        if not iata:
            return None
        if iata not in airline_cache:
            row = db.execute(
                text("SELECT airline_id FROM airlines WHERE iata_code = :code"),
                {"code": iata}
            ).fetchone()
            airline_cache[iata] = row.airline_id if row else None
        return airline_cache[iata]

    # Resolve source_id from name
    source_cache: dict[str, int] = {}

    def get_source_id(source_name: str) -> int | None:
        if source_name not in source_cache:
            row = db.execute(
                text("SELECT source_id FROM sources WHERE name = :name"),
                {"name": source_name}
            ).fetchone()
            source_cache[source_name] = row.source_id if row else None
        return source_cache[source_name]

    insert_sql = text("""
        INSERT INTO fare_observations (
            route_id, airline_id, source_id, departure_date,
            days_to_departure, dtd_bucket, fare_class,
            base_fare, taxes_fees, total_fare, currency,
            collected_at, scrape_batch_id, raw_snapshot_ref
        ) VALUES (
            :route_id, :airline_id, :source_id, :departure_date,
            :days_to_departure, :dtd_bucket, :fare_class,
            :base_fare, :taxes_fees, :total_fare, :currency,
            :collected_at, :scrape_batch_id, :raw_snapshot_ref
        )
        ON CONFLICT ON CONSTRAINT uq_fare_observation_dedup DO NOTHING
    """)

    records = []
    for fare in fares:
        airline_id = get_airline_id(fare.get("carrier_iata"))
        source_id = get_source_id(fare.get("source_name", "Amadeus Test API"))
        if source_id is None:
            logger.warning("Unknown source '%s', skipping fare", fare.get("source_name"))
            continue

        records.append({
            "route_id": fare["route_id"],
            "airline_id": airline_id,
            "source_id": source_id,
            "departure_date": fare["departure_date"],
            "days_to_departure": fare["dtd_bucket"],
            "dtd_bucket": fare["dtd_bucket"],
            "fare_class": fare.get("fare_class", "economy"),
            "base_fare": fare.get("base_fare"),
            "taxes_fees": fare.get("taxes_fees"),
            "total_fare": fare["total_fare"],
            "currency": fare.get("currency", "INR"),
            "collected_at": fare.get("collected_at", datetime.now(timezone.utc)),
            "scrape_batch_id": batch_id,
            "raw_snapshot_ref": fare.get("raw_snapshot_ref"),
        })

    if records:
        result = db.execute(insert_sql, records)
        db.commit()
        inserted = result.rowcount
        logger.info("Loaded %d/%d fare observations (batch %s)", inserted, len(records), batch_id)
        return inserted

    return 0
