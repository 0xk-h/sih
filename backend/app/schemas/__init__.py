from pydantic import BaseModel
from typing import Optional
from datetime import date


# ── Airport ────────────────────────────────────────────────────────────────
class AirportOut(BaseModel):
    airport_id: int
    iata_code: str
    city: Optional[str] = None
    state: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Airline ────────────────────────────────────────────────────────────────
class AirlineOut(BaseModel):
    airline_id: int
    name: str
    iata_code: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Source ─────────────────────────────────────────────────────────────────
class SourceOut(BaseModel):
    source_id: int
    name: str
    source_type: str
    base_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ── RouteWeight ────────────────────────────────────────────────────────────
class RouteWeightOut(BaseModel):
    weight: float
    weight_source: Optional[str] = None
    effective_from: date

    model_config = {"from_attributes": True}


# ── Route ──────────────────────────────────────────────────────────────────
class RouteOut(BaseModel):
    route_id: int
    origin: AirportOut
    destination: AirportOut
    distance_km: Optional[float] = None
    current_weight: Optional[float] = None   # most recent weight

    model_config = {"from_attributes": True}


# ── FareObservation ────────────────────────────────────────────────────────
class FareObservationOut(BaseModel):
    obs_id: int
    route_id: int
    airline_id: Optional[int] = None
    source_id: int
    departure_date: date
    days_to_departure: int
    dtd_bucket: int
    fare_class: Optional[str] = None
    base_fare: Optional[float] = None
    taxes_fees: Optional[float] = None
    total_fare: float
    currency: Optional[str] = "INR"
    collected_at: str

    model_config = {"from_attributes": True}


# ── DailyRoutePrice ────────────────────────────────────────────────────────
class DailyRoutePriceOut(BaseModel):
    route_id: int
    price_date: date
    dtd_bucket: int
    median_fare: Optional[float] = None
    min_fare: Optional[float] = None
    max_fare: Optional[float] = None
    sample_size: Optional[int] = None

    model_config = {"from_attributes": True}


# ── IndexValue ─────────────────────────────────────────────────────────────
class IndexValueOut(BaseModel):
    index_id: int
    index_date: date
    index_scope: str
    scope_ref: Optional[int] = None
    dtd_bucket: Optional[int] = None
    value: float
    base_period: Optional[date] = None
    methodology_version: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Dashboard Summary ──────────────────────────────────────────────────────
class TopMover(BaseModel):
    route_id: int
    route_label: str
    change_pct: float


class DashboardSummary(BaseModel):
    latest_index: float
    index_date: date
    mom_change_pct: Optional[float] = None
    yoy_change_pct: Optional[float] = None
    top_movers: list[TopMover]
    dtd_bucket: int
    methodology_version: str


# ── Data Quality ───────────────────────────────────────────────────────────
class RouteQuality(BaseModel):
    route_id: int
    route_label: str
    dtd_bucket: int
    last_collected_at: Optional[str] = None
    obs_last_24h: int
    obs_last_7d: int
    avg_sample_size: Optional[float] = None


class DataQualityOut(BaseModel):
    generated_at: str
    routes: list[RouteQuality]


# ── Scrape trigger ─────────────────────────────────────────────────────────
class ScrapeTriggerOut(BaseModel):
    batch_id: str
    status: str
    message: str


# ── Airline Comparison ─────────────────────────────────────────────────────
class AirlineMedianOut(BaseModel):
    date: date
    airlines: dict[str, float]
