from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, timedelta
from typing import Optional
from app.db.session import get_db
from app.schemas import IndexValueOut

router = APIRouter(tags=["index"])


@router.get("/index/national", response_model=list[IndexValueOut])
def get_national_index(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    dtd: Optional[int] = Query(None, description="DTD bucket (14 or 1); returns both if omitted"),
    db: Session = Depends(get_db),
):
    """
    Headline national index time series.
    GET /v1/index/national?from=2026-06-01&to=2026-08-27&dtd=14
    """
    clauses = ["index_scope = 'national'"]
    params: dict = {}

    if dtd is not None:
        clauses.append("dtd_bucket = :dtd")
        params["dtd"] = dtd
    if from_date:
        clauses.append("index_date >= :from_date")
        params["from_date"] = from_date
    if to_date:
        clauses.append("index_date <= :to_date")
        params["to_date"] = to_date

    sql = text(f"""
        SELECT index_id, index_date, index_scope, scope_ref, dtd_bucket,
               value, base_period, methodology_version
        FROM index_values
        WHERE {" AND ".join(clauses)}
        ORDER BY dtd_bucket, index_date
    """)

    rows = db.execute(sql, params).fetchall()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No index values found. Run the seed script and index pipeline first."
        )

    return [_row_to_index_out(row) for row in rows]


@router.get("/index/route/{route_id}", response_model=list[IndexValueOut])
def get_route_index(
    route_id: int,
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    dtd: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Route-level index time series.
    GET /v1/index/route/{route_id}?from=2026-06-01&to=2026-08-27
    """
    # Verify route exists
    route_check = db.execute(
        text("SELECT route_id FROM routes WHERE route_id = :rid"),
        {"rid": route_id}
    ).fetchone()
    if not route_check:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")

    clauses = ["index_scope = 'route'", "scope_ref = :route_id"]
    params: dict = {"route_id": route_id}

    if dtd is not None:
        clauses.append("dtd_bucket = :dtd")
        params["dtd"] = dtd
    if from_date:
        clauses.append("index_date >= :from_date")
        params["from_date"] = from_date
    if to_date:
        clauses.append("index_date <= :to_date")
        params["to_date"] = to_date

    sql = text(f"""
        SELECT index_id, index_date, index_scope, scope_ref, dtd_bucket,
               value, base_period, methodology_version
        FROM index_values
        WHERE {" AND ".join(clauses)}
        ORDER BY dtd_bucket, index_date
    """)

    rows = db.execute(sql, params).fetchall()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No index values found for route {route_id}. Run the index pipeline first."
        )

    return [_row_to_index_out(row) for row in rows]


def _row_to_index_out(row) -> IndexValueOut:
    return IndexValueOut(
        index_id=row.index_id,
        index_date=row.index_date,
        index_scope=row.index_scope,
        scope_ref=row.scope_ref,
        dtd_bucket=row.dtd_bucket,
        value=float(row.value),
        base_period=row.base_period,
        methodology_version=row.methodology_version,
    )
