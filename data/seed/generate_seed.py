#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
SEED / DEMO DATA GENERATOR
═══════════════════════════════════════════════════════════════════════════════
THIS IS SYNTHETIC SEED DATA — NOT REAL SCRAPED FARES.
Generated with realistic noise around plausible base fares per route,
with weekend uplift, near-departure premium, and mild weekly inflation drift.
Used to populate 60 days of history for the hackathon demo dashboard.

Per DEVELOPMENT.md §10: "Seeded synthetic historical series (30–60 days,
generated with realistic noise around a handful of real scraped anchor points)
to populate dashboard trend charts — say this openly when presenting."

Run with: python data/seed/generate_seed.py
═══════════════════════════════════════════════════════════════════════════════
"""
import sys
import os
import random
import uuid
from datetime import date, datetime, timedelta, timezone

import numpy as np

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ────────────────────────────────────────────────────────────────────────────
# SEED DATA DEFINITIONS
# ────────────────────────────────────────────────────────────────────────────

AIRPORTS = [
    {"iata_code": "DEL", "city": "New Delhi", "state": "Delhi"},
    {"iata_code": "BOM", "city": "Mumbai", "state": "Maharashtra"},
    {"iata_code": "BLR", "city": "Bengaluru", "state": "Karnataka"},
    {"iata_code": "HYD", "city": "Hyderabad", "state": "Telangana"},
    {"iata_code": "CCU", "city": "Kolkata", "state": "West Bengal"},
    {"iata_code": "GOI", "city": "Goa", "state": "Goa"},
]

AIRLINES = [
    {"name": "IndiGo", "iata_code": "6E"},
    {"name": "Air India", "iata_code": "AI"},
    {"name": "Akasa Air", "iata_code": "QP"},
]

SOURCES = [
    {"name": "Seed Generator", "source_type": "synthetic", "base_url": None},
    {"name": "Amadeus Test API", "source_type": "ota", "base_url": "https://test.api.amadeus.com"},
]

# Routes: (origin_iata, dest_iata, distance_km, dgca_weight)
# Weights from DGCA domestic traffic share (FY24-25, approximate)
# Sum = 0.99 (remainder = 0.01 slack)
ROUTES = [
    ("DEL", "BOM", 1150, 0.28),   # Busiest domestic corridor
    ("DEL", "BLR", 1750, 0.18),
    ("BOM", "BLR",  980, 0.14),
    ("DEL", "HYD", 1260, 0.13),
    ("DEL", "CCU", 1305, 0.12),
    ("BOM", "GOI",  595, 0.10),
]

# Base fares per route in INR (realistic anchor points, economy class)
# DTD=14 bucket: advance purchase, lower fares
# DTD=1 bucket: near-departure, higher fares (last-minute premium)
BASE_FARES = {
    "DEL-BOM": {14: 4500, 1: 7200},
    "DEL-BLR": {14: 5200, 1: 8500},
    "BOM-BLR": {14: 3800, 1: 6100},
    "DEL-HYD": {14: 4100, 1: 6800},
    "DEL-CCU": {14: 4800, 1: 7600},
    "BOM-GOI": {14: 3200, 1: 5400},
}

DTD_BUCKETS = [14, 1]
FARE_CLASSES = ["economy", "economy", "economy", "premium_economy"]  # weighted towards economy
SEED_DAYS = 60  # 60-day history per DEVELOPMENT.md §10


def generate_seed_fare(
    base_fare: float,
    day_offset: int,
    weekday: int,
    dtd_bucket: int,
    noise_pct: float = 0.08,
) -> float:
    """
    Generate a single synthetic fare with:
    - Gaussian noise (σ = noise_pct of base)
    - Weekend uplift (+12% on Fri/Sat/Sun departures)
    - Weekly inflation drift (+0.5% per week = mild CPI-like trend)
    - Near-departure premium already encoded in BASE_FARES DTD=1 values

    NOTE: ALL VALUES ARE SYNTHETIC — see module docstring.
    """
    # Weekly drift: simulate ~0.5% inflation per week
    week_number = day_offset // 7
    drift_multiplier = 1.0 + (week_number * 0.005)

    # Weekend uplift
    weekend_multiplier = 1.12 if weekday in (4, 5, 6) else 1.0  # Fri=4, Sat=5, Sun=6

    # Gaussian noise
    noise = np.random.normal(0, noise_pct * base_fare)

    synthetic_fare = base_fare * drift_multiplier * weekend_multiplier + noise

    # Never let fare go below 60% of base (floor for realism)
    synthetic_fare = max(synthetic_fare, base_fare * 0.6)

    return round(synthetic_fare, 2)


def run_seed():
    """Main seed function — wipes existing seed data and regenerates."""
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    print("═" * 70)
    print("AIRFARE INDEX — SEED DATA GENERATOR")
    print("THIS IS SYNTHETIC DEMO DATA — NOT REAL SCRAPED FARES")
    print("═" * 70)

    try:
        # ── 1. Insert airports ────────────────────────────────────────────
        print("\n[1/7] Seeding airports...")
        airport_ids: dict[str, int] = {}
        for ap in AIRPORTS:
            result = db.execute(text("""
                INSERT INTO airports (iata_code, city, state)
                VALUES (:iata_code, :city, :state)
                ON CONFLICT (iata_code) DO UPDATE SET city=EXCLUDED.city, state=EXCLUDED.state
                RETURNING airport_id
            """), ap).fetchone()
            airport_ids[ap["iata_code"]] = result.airport_id
        db.commit()
        print(f"  → {len(airport_ids)} airports seeded: {list(airport_ids.keys())}")

        # ── 2. Insert airlines ────────────────────────────────────────────
        print("\n[2/7] Seeding airlines...")
        airline_ids: list[int] = []
        for al in AIRLINES:
            result = db.execute(text("""
                INSERT INTO airlines (name, iata_code)
                VALUES (:name, :iata_code)
                ON CONFLICT DO NOTHING
                RETURNING airline_id
            """), al).fetchone()
            if result:
                airline_ids.append(result.airline_id)
        if not airline_ids:
            # Already exist — fetch them
            rows = db.execute(text("SELECT airline_id FROM airlines ORDER BY airline_id")).fetchall()
            airline_ids = [r.airline_id for r in rows]
        db.commit()
        print(f"  → {len(airline_ids)} airlines seeded")

        # ── 3. Insert sources ─────────────────────────────────────────────
        print("\n[3/7] Seeding sources...")
        source_ids: list[int] = []
        for src in SOURCES:
            result = db.execute(text("""
                INSERT INTO sources (name, source_type, base_url)
                VALUES (:name, :source_type, :base_url)
                ON CONFLICT DO NOTHING
                RETURNING source_id
            """), src).fetchone()
            if result:
                source_ids.append(result.source_id)
        if not source_ids:
            rows = db.execute(text("SELECT source_id FROM sources ORDER BY source_id")).fetchall()
            source_ids = [r.source_id for r in rows]
        db.commit()
        print(f"  → {len(source_ids)} sources seeded")

        # ── 4. Insert routes ──────────────────────────────────────────────
        print("\n[4/7] Seeding routes...")
        route_ids: dict[str, int] = {}
        for origin_iata, dest_iata, distance_km, weight in ROUTES:
            orig_id = airport_ids[origin_iata]
            dest_id = airport_ids[dest_iata]
            # Check if route already exists to prevent duplicates on rebuild
            existing = db.execute(text("""
                SELECT route_id FROM routes
                WHERE origin_airport_id = :orig AND dest_airport_id = :dest
            """), {"orig": orig_id, "dest": dest_id}).fetchone()
            if existing:
                route_ids[f"{origin_iata}-{dest_iata}"] = existing.route_id
            else:
                result = db.execute(text("""
                    INSERT INTO routes (origin_airport_id, dest_airport_id, distance_km)
                    VALUES (:orig, :dest, :dist)
                    RETURNING route_id
                """), {"orig": orig_id, "dest": dest_id, "dist": distance_km}).fetchone()
                route_ids[f"{origin_iata}-{dest_iata}"] = result.route_id
        db.commit()
        print(f"  → {len(route_ids)} routes seeded: {list(route_ids.keys())}")

        # ── 5. Insert route weights ───────────────────────────────────────
        print("\n[5/7] Seeding route weights (DGCA FY25 traffic share)...")
        effective_from = date(2025, 4, 1)  # Start of FY25
        for origin_iata, dest_iata, _, weight in ROUTES:
            route_label = f"{origin_iata}-{dest_iata}"
            route_id = route_ids.get(route_label)
            if route_id:
                db.execute(text("""
                    INSERT INTO route_weights (route_id, weight, weight_source, effective_from)
                    VALUES (:route_id, :weight, :source, :eff_from)
                    ON CONFLICT (route_id, effective_from) DO UPDATE SET weight=EXCLUDED.weight
                """), {
                    "route_id": route_id,
                    "weight": weight,
                    "source": "DGCA FY25 domestic traffic share (synthetic seed)",
                    "eff_from": effective_from,
                })
        db.commit()
        print(f"  → Weights set. Sum = {sum(r[3] for r in ROUTES):.2f}")

        # ── 6. Clear existing seed observations ───────────────────────────
        print("\n[6/7] Clearing old seed observations...")
        seed_source_id = source_ids[0]  # First source = "Seed Generator"
        deleted = db.execute(text("""
            DELETE FROM fare_observations WHERE source_id = :sid
        """), {"sid": seed_source_id}).rowcount
        db.execute(text("DELETE FROM daily_route_price"))
        db.execute(text("DELETE FROM index_values"))
        db.commit()
        print(f"  → Cleared {deleted} old observations, daily prices, and index values")

        # ── 7. Generate 60-day fare observations ─────────────────────────
        print("\n[7/7] Generating synthetic fare observations (SEED DATA)...")
        print("      NOTE: All fares below are synthetically generated — see module docstring")

        today = date.today()
        batch_id = uuid.uuid4()
        obs_count = 0
        np.random.seed(42)  # Reproducible seed

        obs_batch = []

        for day_offset in range(SEED_DAYS):
            obs_date = today - timedelta(days=SEED_DAYS - day_offset - 1)
            weekday = obs_date.weekday()

            for route_label, route_id in route_ids.items():
                base_fares_for_route = BASE_FARES.get(route_label, {14: 5000, 1: 8000})

                for dtd_bucket in DTD_BUCKETS:
                    # Departure date = obs_date + dtd_bucket (approximate)
                    departure_date = obs_date + timedelta(days=dtd_bucket)
                    base_fare = base_fares_for_route.get(dtd_bucket, 5000)

                    # Generate 3 observations per route/dtd/day (one per airline)
                    for airline_id in airline_ids:
                        fare_class = random.choice(FARE_CLASSES)
                        total_fare = generate_seed_fare(
                            base_fare=base_fare,
                            day_offset=day_offset,
                            weekday=weekday,
                            dtd_bucket=dtd_bucket,
                        )
                        # Rough tax breakdown: ~18% of total
                        taxes = round(total_fare * 0.18, 2)
                        base = round(total_fare - taxes, 2)

                        # collected_at = noon on obs_date (IST = UTC+5:30)
                        collected_at = datetime(
                            obs_date.year, obs_date.month, obs_date.day,
                            6, 30, 0, tzinfo=timezone.utc  # 6:30 UTC = 12:00 IST
                        )

                        obs_batch.append({
                            "route_id": route_id,
                            "airline_id": airline_id,
                            "source_id": seed_source_id,
                            "departure_date": departure_date,
                            "days_to_departure": dtd_bucket,
                            "dtd_bucket": dtd_bucket,
                            "fare_class": fare_class,
                            "base_fare": base,
                            "taxes_fees": taxes,
                            "total_fare": total_fare,
                            "currency": "INR",
                            "collected_at": collected_at,
                            "scrape_batch_id": batch_id,
                            "raw_snapshot_ref": f"SEED_DATA/{route_label}/dtd{dtd_bucket}/{obs_date}",
                        })

        # Bulk insert
        if obs_batch:
            db.execute(text("""
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
            """), obs_batch)
            db.commit()
            obs_count = len(obs_batch)

        print(f"  → Generated {obs_count} synthetic fare observations")
        print(f"  → Routes: {len(route_ids)}, Days: {SEED_DAYS}, DTD buckets: {DTD_BUCKETS}, Airlines: {len(airline_ids)}")

        # ── 8. Run index pipeline ─────────────────────────────────────────
        print("\n[+] Running index computation pipeline on seeded data...")
        from app.services.index_engine.runner import run_full_pipeline
        results = run_full_pipeline(db)

        for dtd, res in results.items():
            n = len(res.get("national", []))
            print(f"    DTD={dtd}: {n} national index points computed")

        print("\n" + "═" * 70)
        print("SEED COMPLETE — Dashboard should now show 60 days of index data")
        print("Remember: this is SYNTHETIC SEED DATA for demo purposes")
        print("═" * 70)

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
