from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, timedelta
from app.db.session import get_db
from app.schemas import DashboardSummary, TopMover

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Latest index value, MoM/YoY change, top movers per route.
    GET /v1/dashboard/summary
    """
    # Get latest national index for DTD=14 (primary bucket)
    latest_sql = text("""
        SELECT iv.index_date, iv.value, iv.dtd_bucket, iv.base_period, iv.methodology_version
        FROM index_values iv
        WHERE iv.index_scope = 'national' AND iv.dtd_bucket = 14
        ORDER BY iv.index_date DESC
        LIMIT 1
    """)
    latest = db.execute(latest_sql).fetchone()
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No index values found. Run seed + pipeline first."
        )

    latest_val = float(latest.value)
    latest_date: date = latest.index_date

    # MoM: ~30 days ago
    mom_date = latest_date - timedelta(days=30)
    mom_sql = text("""
        SELECT value FROM index_values
        WHERE index_scope = 'national' AND dtd_bucket = 14
          AND index_date >= :mom_date
        ORDER BY index_date ASC
        LIMIT 1
    """)
    mom_row = db.execute(mom_sql, {"mom_date": mom_date}).fetchone()
    mom_change = None
    if mom_row:
        mom_val = float(mom_row.value)
        mom_change = round(((latest_val - mom_val) / mom_val) * 100, 2) if mom_val else None

    # YoY: not available in 60-day demo, omit
    yoy_change = None

    # Top movers: route-level, last 30 days
    movers_sql = text("""
        WITH latest_route AS (
            SELECT scope_ref AS route_id, value,
                   ROW_NUMBER() OVER (PARTITION BY scope_ref ORDER BY index_date DESC) AS rn
            FROM index_values
            WHERE index_scope = 'route' AND dtd_bucket = 14
        ),
        prev_route AS (
            SELECT scope_ref AS route_id, value,
                   ROW_NUMBER() OVER (PARTITION BY scope_ref ORDER BY index_date ASC) AS rn
            FROM index_values
            WHERE index_scope = 'route' AND dtd_bucket = 14
              AND index_date >= (CURRENT_DATE - INTERVAL '30 days')
        ),
        orig AS (SELECT airport_id, iata_code FROM airports),
        dest AS (SELECT airport_id, iata_code FROM airports)
        SELECT
            l.route_id,
            o.iata_code || '-' || d.iata_code AS route_label,
            l.value AS latest_val,
            p.value AS prev_val,
            CASE WHEN p.value > 0
                 THEN ROUND(((l.value - p.value) / p.value * 100)::numeric, 2)
                 ELSE 0 END AS change_pct
        FROM latest_route l
        JOIN prev_route p ON p.route_id = l.route_id AND l.rn = 1 AND p.rn = 1
        JOIN routes r ON r.route_id = l.route_id
        JOIN orig o ON o.airport_id = r.origin_airport_id
        JOIN dest d ON d.airport_id = r.dest_airport_id
        ORDER BY ABS(
            CASE WHEN p.value > 0
                 THEN ((l.value - p.value) / p.value * 100)
                 ELSE 0 END
        ) DESC
        LIMIT 5
    """)
    mover_rows = db.execute(movers_sql).fetchall()
    top_movers = [
        TopMover(
            route_id=row.route_id,
            route_label=row.route_label,
            change_pct=float(row.change_pct),
        )
        for row in mover_rows
    ]

    return DashboardSummary(
        latest_index=round(latest_val, 2),
        index_date=latest_date,
        mom_change_pct=mom_change,
        yoy_change_pct=yoy_change,
        top_movers=top_movers,
        dtd_bucket=14,
        methodology_version=latest.methodology_version or "laspeyres-chain-v1",
    )
