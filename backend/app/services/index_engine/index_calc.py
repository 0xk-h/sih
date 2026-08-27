"""
Index Engine — Index Calculator
Implements Laspeyres chain-linked national index per DEVELOPMENT.md §3.3–3.4.

Algorithm (per spec):
  Step 1: Route relative vs base period
      I_r(t, b) = P(r, t, b) / P(r, base_date, b) × 100

  Step 2: Chain-linked Laspeyres national index
      I(t) = I(t-1) × Σ_r [ w_r × P_r(t) / P_r(t-1) ]

Results are stored in index_values with index_scope='national' or 'route'.
"""
import pandas as pd
import numpy as np
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

METHODOLOGY_VERSION = "laspeyres-chain-v1"


def compute_index(
    db: Session,
    dtd_bucket: int,
    from_date: date | None = None,
    to_date: date | None = None,
    base_date: date | None = None,
) -> dict:
    """
    Full index computation pipeline for a single DTD bucket.
    Returns dict with 'national' and 'route' time series.
    """
    # 1. Load daily_route_price and weights
    daily_df = _load_daily_prices(db, dtd_bucket, from_date, to_date)
    if daily_df.empty:
        logger.warning("No daily prices found for dtd_bucket=%d", dtd_bucket)
        return {"national": [], "route": {}}

    weights = _load_weights(db)
    if not weights:
        logger.error("No route weights found — cannot compute index")
        return {"national": [], "route": {}}

    # Only include routes that have both prices AND weights
    active_routes = set(daily_df["route_id"].unique()) & set(weights.keys())
    if not active_routes:
        logger.error("No overlap between priced routes and weighted routes")
        return {"national": [], "route": {}}

    # Normalize weights to sum to 1 over active routes
    raw_weights = {r: weights[r] for r in active_routes}
    total_w = sum(raw_weights.values())
    norm_weights = {r: w / total_w for r, w in raw_weights.items()}

    # Pivot: rows=date, cols=route_id
    pivot = (
        daily_df[daily_df["route_id"].isin(active_routes)]
        .pivot_table(index="price_date", columns="route_id", values="median_fare")
        .sort_index()
    )

    # Determine base period
    if base_date is None:
        base_date = pivot.index.min()

    base_prices = pivot.loc[pivot.index == base_date].squeeze()
    if isinstance(base_prices, pd.DataFrame):
        base_prices = base_prices.iloc[0]

    dates = pivot.index.tolist()
    if len(dates) < 2:
        logger.warning("Not enough date points to compute chain-linked index")
        return {"national": [], "route": {}}

    def _safe_get_pivot(pivot_df, row_key, col_key):
        """Safely get value from 2D pivot DataFrame."""
        try:
            val = pivot_df.at[row_key, col_key]
            return float(val) if val is not None and not pd.isna(val) else None
        except (KeyError, TypeError, ValueError):
            return None

    def _safe_get_series(series, key):
        """Safely get value from 1D Series by key."""
        try:
            val = series[key]
            return float(val) if val is not None and not pd.isna(val) else None
        except (KeyError, TypeError, ValueError):
            return None

    # ── Route-level relatives ───────────────────────────────────────────────
    route_relatives: dict[int, list[dict]] = {r: [] for r in active_routes}
    for d in dates:
        for r in active_routes:
            price = _safe_get_pivot(pivot, d, r)
            base_p = _safe_get_series(base_prices, r)
            if price is not None and base_p and base_p > 0:
                rel = (price / base_p) * 100
            else:
                rel = None
            route_relatives[r].append({"date": d, "value": rel})

    # ── Chain-linked national index ─────────────────────────────────────────
    # I(base) = 100
    # I(t) = I(t-1) × Σ_r [ w_r × P_r(t) / P_r(t-1) ]
    national_index: list[dict] = []
    prev_index = 100.0

    for i, d in enumerate(dates):
        if i == 0:
            national_index.append({"date": d, "value": 100.0})
            continue

        prev_d = dates[i - 1]
        chain_link_sum = 0.0
        weight_used = 0.0

        for r in active_routes:
            p_t = _safe_get_pivot(pivot, d, r)
            p_prev = _safe_get_pivot(pivot, prev_d, r)
            if p_t is not None and p_prev is not None and p_prev > 0:
                chain_link_sum += norm_weights[r] * (p_t / p_prev)
                weight_used += norm_weights[r]

        if weight_used > 0:
            # Re-normalize the link ratio to account for missing routes
            chain_ratio = chain_link_sum / weight_used
            new_index = prev_index * chain_ratio
        else:
            new_index = prev_index

        national_index.append({"date": d, "value": round(new_index, 4)})
        prev_index = new_index

    # ── Persist to index_values ─────────────────────────────────────────────
    _upsert_index_values(db, national_index, route_relatives, dtd_bucket, base_date)

    return {
        "national": national_index,
        "route": route_relatives,
    }


def _load_daily_prices(
    db: Session, dtd_bucket: int, from_date: date | None, to_date: date | None
) -> pd.DataFrame:
    """Load daily_route_price for the given dtd_bucket and date range."""
    clauses = ["dtd_bucket = :dtd"]
    params: dict = {"dtd": dtd_bucket}
    if from_date:
        clauses.append("price_date >= :from_date")
        params["from_date"] = from_date
    if to_date:
        clauses.append("price_date <= :to_date")
        params["to_date"] = to_date

    sql = text(f"""
        SELECT route_id, price_date, median_fare
        FROM daily_route_price
        WHERE {" AND ".join(clauses)}
        ORDER BY route_id, price_date
    """)
    rows = db.execute(sql, params).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["route_id", "price_date", "median_fare"])
    df["price_date"] = pd.to_datetime(df["price_date"]).dt.date
    df["median_fare"] = df["median_fare"].astype(float)
    return df


def _load_weights(db: Session) -> dict[int, float]:
    """Load the most recent route weights."""
    sql = text("""
        SELECT DISTINCT ON (route_id) route_id, weight
        FROM route_weights
        ORDER BY route_id, effective_from DESC
    """)
    rows = db.execute(sql).fetchall()
    return {int(r.route_id): float(r.weight) for r in rows}


def _upsert_index_values(
    db: Session,
    national_series: list[dict],
    route_series: dict[int, list[dict]],
    dtd_bucket: int,
    base_period: date,
) -> None:
    """Upsert computed index values into index_values table."""
    upsert_sql = text("""
        INSERT INTO index_values
            (index_date, index_scope, scope_ref, dtd_bucket, value, base_period, methodology_version)
        VALUES
            (:index_date, :index_scope, :scope_ref, :dtd_bucket, :value, :base_period, :methodology_version)
        ON CONFLICT DO NOTHING
    """)

    records = []

    # National index
    for entry in national_series:
        if entry["value"] is not None:
            records.append({
                "index_date": entry["date"],
                "index_scope": "national",
                "scope_ref": None,
                "dtd_bucket": dtd_bucket,
                "value": float(entry["value"]),
                "base_period": base_period,
                "methodology_version": METHODOLOGY_VERSION,
            })

    # Route-level index
    for route_id, series in route_series.items():
        for entry in series:
            if entry["value"] is not None:
                records.append({
                    "index_date": entry["date"],
                    "index_scope": "route",
                    "scope_ref": int(route_id),
                    "dtd_bucket": dtd_bucket,
                    "value": float(entry["value"]),
                    "base_period": base_period,
                    "methodology_version": METHODOLOGY_VERSION,
                })

    if records:
        # Delete existing values for same scope/dtd before upserting
        db.execute(text("""
            DELETE FROM index_values
            WHERE index_scope = 'national' AND dtd_bucket = :dtd
        """), {"dtd": dtd_bucket})
        db.execute(text("""
            DELETE FROM index_values
            WHERE index_scope = 'route' AND dtd_bucket = :dtd
        """), {"dtd": dtd_bucket})
        db.execute(upsert_sql, records)
        db.commit()
        logger.info("Upserted %d index value records", len(records))
