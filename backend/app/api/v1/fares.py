from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date
from typing import Optional
from app.db.session import get_db
from app.schemas import FareObservationOut

router = APIRouter(tags=["fares"])


@router.get("/fares/{route_id}", response_model=list[FareObservationOut])
def get_fares(
    route_id: int,
    dtd: Optional[int] = Query(None, description="Filter by DTD bucket (14 or 1)"),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    limit: int = Query(500, le=5000),
    db: Session = Depends(get_db),
):
    """
    Raw/cleaned fare series for a route.
    GET /v1/fares/{route_id}?dtd=14&from=2026-06-01&to=2026-08-27
    """
    # Verify route exists
    route_check = db.execute(
        text("SELECT route_id FROM routes WHERE route_id = :rid"),
        {"rid": route_id}
    ).fetchone()
    if not route_check:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")

    clauses = ["route_id = :route_id"]
    params: dict = {"route_id": route_id}

    if dtd is not None:
        clauses.append("dtd_bucket = :dtd")
        params["dtd"] = dtd
    if from_date:
        clauses.append("departure_date >= :from_date")
        params["from_date"] = from_date
    if to_date:
        clauses.append("departure_date <= :to_date")
        params["to_date"] = to_date

    params["limit"] = limit

    sql = text(f"""
        SELECT
            obs_id, route_id, airline_id, source_id,
            departure_date, days_to_departure, dtd_bucket,
            fare_class, base_fare, taxes_fees, total_fare,
            currency, collected_at
        FROM fare_observations
        WHERE {" AND ".join(clauses)}
        ORDER BY departure_date DESC, collected_at DESC
        LIMIT :limit
    """)

    rows = db.execute(sql, params).fetchall()

    return [
        FareObservationOut(
            obs_id=row.obs_id,
            route_id=row.route_id,
            airline_id=row.airline_id,
            source_id=row.source_id,
            departure_date=row.departure_date,
            days_to_departure=row.days_to_departure,
            dtd_bucket=row.dtd_bucket,
            fare_class=row.fare_class,
            base_fare=float(row.base_fare) if row.base_fare else None,
            taxes_fees=float(row.taxes_fees) if row.taxes_fees else None,
            total_fare=float(row.total_fare),
            currency=row.currency,
            collected_at=row.collected_at.isoformat(),
        )
        for row in rows
    ]
