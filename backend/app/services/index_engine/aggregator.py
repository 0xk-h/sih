"""
Index Engine — Aggregator
Turns fare_observations (silver layer) → daily_route_price (gold layer).

Step 1 of the index pipeline per DEVELOPMENT.md §8.
P(r, t, b) = median(all normalized total fares collected for route r, date t, dtd_bucket b)
"""
import pandas as pd
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

DTD_BUCKETS = [14, 1]  # MVP scope — 2 buckets only


def aggregate_to_daily_route_price(
    db: Session,
    from_date: date | None = None,
    to_date: date | None = None,
) -> pd.DataFrame:
    """
    Pull fare_observations for the given date range, aggregate to daily
    median/min/max/count per (route_id, departure_date, dtd_bucket).

    Returns a DataFrame; also upserts results into daily_route_price table.
    """
    where_clauses = ["dtd_bucket = ANY(:buckets)"]
    params: dict = {"buckets": DTD_BUCKETS}

    if from_date:
        where_clauses.append("departure_date >= :from_date")
        params["from_date"] = from_date
    if to_date:
        where_clauses.append("departure_date <= :to_date")
        params["to_date"] = to_date

    where_sql = " AND ".join(where_clauses)

    query = text(f"""
        SELECT
            route_id,
            departure_date,
            dtd_bucket,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_fare) AS median_fare,
            MIN(total_fare) AS min_fare,
            MAX(total_fare) AS max_fare,
            COUNT(*)::int AS sample_size
        FROM fare_observations
        WHERE {where_sql}
        GROUP BY route_id, departure_date, dtd_bucket
        ORDER BY route_id, departure_date, dtd_bucket
    """)

    result = db.execute(query, params)
    rows = result.fetchall()

    if not rows:
        logger.warning("aggregate_to_daily_route_price: no fare observations found")
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "route_id", "departure_date", "dtd_bucket",
        "median_fare", "min_fare", "max_fare", "sample_size"
    ])

    # Upsert into daily_route_price
    _upsert_daily_route_price(db, df)

    logger.info(
        "Aggregated %d route/date/dtd combinations into daily_route_price", len(df)
    )
    return df


def _upsert_daily_route_price(db: Session, df: pd.DataFrame) -> None:
    """Upsert aggregated prices into daily_route_price using ON CONFLICT."""
    upsert_sql = text("""
        INSERT INTO daily_route_price
            (route_id, price_date, dtd_bucket, median_fare, min_fare, max_fare, sample_size)
        VALUES
            (:route_id, :price_date, :dtd_bucket, :median_fare, :min_fare, :max_fare, :sample_size)
        ON CONFLICT (route_id, price_date, dtd_bucket)
        DO UPDATE SET
            median_fare = EXCLUDED.median_fare,
            min_fare = EXCLUDED.min_fare,
            max_fare = EXCLUDED.max_fare,
            sample_size = EXCLUDED.sample_size
    """)

    records = [
        {
            "route_id": int(row.route_id),
            "price_date": row.departure_date,
            "dtd_bucket": int(row.dtd_bucket),
            "median_fare": float(row.median_fare) if row.median_fare is not None else None,
            "min_fare": float(row.min_fare) if row.min_fare is not None else None,
            "max_fare": float(row.max_fare) if row.max_fare is not None else None,
            "sample_size": int(row.sample_size) if row.sample_size is not None else None,
        }
        for row in df.itertuples()
    ]

    if records:
        db.execute(upsert_sql, records)
        db.commit()
