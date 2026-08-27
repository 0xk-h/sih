from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from app.db.session import get_db
from app.schemas import DataQualityOut, RouteQuality

router = APIRouter(tags=["data-quality"])


@router.get("/data-quality", response_model=DataQualityOut)
def get_data_quality(db: Session = Depends(get_db)):
    """
    Sample sizes, last scrape times, coverage gaps per route/dtd_bucket.
    GET /v1/data-quality
    Builds trust by exposing the measurement metadata — required for CPI-adjacent tools.
    """
    sql = text("""
        WITH route_info AS (
            SELECT
                r.route_id,
                o.iata_code || '-' || d.iata_code AS route_label
            FROM routes r
            JOIN airports o ON o.airport_id = r.origin_airport_id
            JOIN airports d ON d.airport_id = r.dest_airport_id
        ),
        obs_stats AS (
            SELECT
                fo.route_id,
                fo.dtd_bucket,
                MAX(fo.collected_at) AS last_collected_at,
                COUNT(*) FILTER (
                    WHERE fo.collected_at >= NOW() - INTERVAL '24 hours'
                ) AS obs_last_24h,
                COUNT(*) FILTER (
                    WHERE fo.collected_at >= NOW() - INTERVAL '7 days'
                ) AS obs_last_7d
            FROM fare_observations fo
            GROUP BY fo.route_id, fo.dtd_bucket
        ),
        daily_avg AS (
            SELECT route_id, dtd_bucket, AVG(sample_size) AS avg_sample_size
            FROM daily_route_price
            GROUP BY route_id, dtd_bucket
        )
        SELECT
            ri.route_id,
            ri.route_label,
            COALESCE(os.dtd_bucket, da.dtd_bucket) AS dtd_bucket,
            os.last_collected_at,
            COALESCE(os.obs_last_24h, 0) AS obs_last_24h,
            COALESCE(os.obs_last_7d, 0) AS obs_last_7d,
            da.avg_sample_size
        FROM route_info ri
        CROSS JOIN (VALUES (14), (1)) AS b(dtd_bucket)
        LEFT JOIN obs_stats os ON os.route_id = ri.route_id AND os.dtd_bucket = b.dtd_bucket
        LEFT JOIN daily_avg da ON da.route_id = ri.route_id AND da.dtd_bucket = b.dtd_bucket
        ORDER BY ri.route_id, dtd_bucket
    """)

    rows = db.execute(sql).fetchall()

    quality_rows = [
        RouteQuality(
            route_id=row.route_id,
            route_label=row.route_label,
            dtd_bucket=row.dtd_bucket,
            last_collected_at=row.last_collected_at.isoformat() if row.last_collected_at else None,
            obs_last_24h=row.obs_last_24h or 0,
            obs_last_7d=row.obs_last_7d or 0,
            avg_sample_size=float(row.avg_sample_size) if row.avg_sample_size else None,
        )
        for row in rows
    ]

    return DataQualityOut(
        generated_at=datetime.now(timezone.utc).isoformat(),
        routes=quality_rows,
    )
