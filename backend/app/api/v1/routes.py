from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.db.session import get_db
from app.schemas import RouteOut, AirportOut

router = APIRouter(tags=["routes"])


@router.get("/routes", response_model=list[RouteOut])
def list_routes(db: Session = Depends(get_db)):
    """
    List all tracked routes with their current DGCA-derived basket weights.
    GET /v1/routes
    """
    sql = text("""
        SELECT
            r.route_id,
            r.distance_km,
            orig.airport_id AS orig_id,
            orig.iata_code AS orig_iata,
            orig.city AS orig_city,
            orig.state AS orig_state,
            dest.airport_id AS dest_id,
            dest.iata_code AS dest_iata,
            dest.city AS dest_city,
            dest.state AS dest_state,
            w.weight AS current_weight
        FROM routes r
        JOIN airports orig ON orig.airport_id = r.origin_airport_id
        JOIN airports dest ON dest.airport_id = r.dest_airport_id
        LEFT JOIN LATERAL (
            SELECT weight FROM route_weights
            WHERE route_id = r.route_id
            ORDER BY effective_from DESC
            LIMIT 1
        ) w ON TRUE
        ORDER BY w.weight DESC NULLS LAST
    """)

    rows = db.execute(sql).fetchall()

    return [
        RouteOut(
            route_id=row.route_id,
            distance_km=float(row.distance_km) if row.distance_km else None,
            current_weight=float(row.current_weight) if row.current_weight else None,
            origin=AirportOut(
                airport_id=row.orig_id,
                iata_code=row.orig_iata,
                city=row.orig_city,
                state=row.orig_state,
            ),
            destination=AirportOut(
                airport_id=row.dest_id,
                iata_code=row.dest_iata,
                city=row.dest_city,
                state=row.dest_state,
            ),
        )
        for row in rows
    ]


@router.get("/routes/{route_id}/airline-medians", response_model=list[dict])
def get_airline_medians(
    route_id: int,
    dtd: int = 14,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Calculate median fare per airline for a given route over the last N days.
    """
    sql = text("""
        WITH daily_airline_fares AS (
            SELECT
                f.departure_date AS date,
                a.name AS airline_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.total_fare) AS median_fare
            FROM fare_observations f
            JOIN airlines a ON a.airline_id = f.airline_id
            WHERE f.route_id = :route_id
              AND f.dtd_bucket = :dtd
              AND f.departure_date >= (CURRENT_DATE - INTERVAL '1 day' * :days)
            GROUP BY f.departure_date, a.name
        )
        SELECT date, airline_name, median_fare
        FROM daily_airline_fares
        ORDER BY date ASC
    """)
    
    rows = db.execute(sql, {"route_id": route_id, "dtd": dtd, "days": days}).fetchall()
    
    # Restructure into {date: date, airlines: {airline_name: median_fare, ...}}
    grouped = {}
    for row in rows:
        d = row.date
        if d not in grouped:
            grouped[d] = {}
        grouped[d][row.airline_name] = float(row.median_fare)
        
    result = []
    for d, airlines in sorted(grouped.items()):
        result.append({
            "date": d,
            "airlines": airlines
        })
        
    return result
