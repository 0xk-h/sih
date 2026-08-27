# Real-Time Airfare Price Index for India
**SIH26056 | Team Runtime Rulers | Theme: Travel & Tourism**

A Laspeyres chain-linked weighted national airfare price index across India's top domestic routes — built like CPI, for airfares.

> ⚠️ **Demo dataset notice**: The historical time series in this prototype is **synthetic seed data** generated with realistic noise and inflation drift (see §10 of DEVELOPMENT.md). This is stated openly — judges are expected to ask about it. Real collection via Amadeus API activates with credentials.

---

## Architecture

```
Scrapers (Amadeus API + stubs)
    ↓
fare_observations  [silver layer — every row has collected_at + dtd_bucket]
    ↓
daily_route_price  [gold layer — median/min/max/count per route/date/dtd]
    ↓
index_values       [published — national + route Laspeyres chain-linked index]
    ↓
React Dashboard    [Overview + Route Explorer + Data Quality + Methodology]
```

## Quick Start (Docker)

```bash
# 1. Clone and enter
git clone <repo> && cd airfare-index

# 2. Copy env file and add Amadeus credentials (optional for seed-only mode)
cp backend/.env.example backend/.env
# Edit backend/.env and set AMADEUS_CLIENT_ID, AMADEUS_CLIENT_SECRET

# 3. Start everything
docker compose up --build

# Services:
#   Backend API:  http://localhost:8000
#   API Docs:     http://localhost:8000/docs
#   Frontend:     http://localhost:5173
```

On first start, Docker Compose will:
1. Start Postgres
2. Run Alembic migrations (create all 8 tables)
3. Run the seed script (60 days of synthetic fare history)
4. Compute the full index pipeline
5. Start the FastAPI server (+ 6-hour scheduled recomputation)
6. Start the Vite frontend

---

## Manual Setup (without Docker)

### Prerequisites
- Python 3.12+
- Node 20+
- PostgreSQL 15+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set env vars
cp .env.example .env
# Edit .env with your DATABASE_URL and Amadeus credentials

# Run migrations
alembic upgrade head

# Seed 60 days of historical data + compute initial index
python ../data/seed/generate_seed.py

# Start API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Run the scheduler (optional)

```bash
# In a separate terminal with venv activated
cd backend
python ../scraper/scheduler.py
# Fetches live Amadeus fares every 6 hours and recomputes index
```

---

## Seed Script

```bash
# Re-run to regenerate 60 days of synthetic history
python data/seed/generate_seed.py
```

The seed script:
- Inserts airports, airlines, sources, routes, route_weights
- Generates 60 × 6 routes × 2 DTD buckets × 3 airlines = **2,160 synthetic fare observations**
- Each observation has realistic base fares, Gaussian noise (σ=8%), weekend uplift (+12%), weekly drift (+0.5%/week)
- Runs the full index pipeline after seeding (aggregation → chain-linked index computation)
- Clears old seed data on each run so re-runs are safe

---

## API Reference

Base URL: `http://localhost:8000/v1`
Interactive docs: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/routes` | All routes with DGCA weights |
| `GET` | `/fares/{route_id}?dtd=&from=&to=` | Fare observations |
| `GET` | `/index/national?from=&to=&dtd=` | National index time series |
| `GET` | `/index/route/{route_id}?from=&to=` | Route-level index |
| `GET` | `/dashboard/summary` | Latest value, MoM change, top movers |
| `POST` | `/scrape/trigger` | Trigger index recompute (demo) |
| `GET` | `/data-quality` | Coverage, sample sizes, staleness |

---

## Amadeus API Setup

1. Register at https://developers.amadeus.com (free)
2. Create a new app → copy `Client ID` and `Client Secret`
3. Add to `backend/.env`:
   ```
   AMADEUS_CLIENT_ID=your_client_id
   AMADEUS_CLIENT_SECRET=your_client_secret
   ```
4. Restart the backend — the scheduler will automatically fetch real fares

Amadeus sandbox: ~500 requests/day, free tier, no real booking capability.

---

## Index Methodology

See [docs/methodology.md](docs/methodology.md) and the **Methodology** page in the dashboard.

**TL;DR**: Laspeyres chain-linked weighted index — same mathematical structure as India's CPI:
- Median fare per route/day/DTD bucket (robust to outliers)
- Route relative vs base period (I = P_t / P_base × 100)  
- Weighted aggregate: I(t) = I(t−1) × Σ [w_r × P_r(t)/P_r(t−1)]
- Weights from DGCA FY25 domestic traffic share

**DTD comparability**: Fares at different booking windows are tracked as separate series — you never average a 45-day advance fare with a same-day fare.

---

## Project Structure

```
airfare-index/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + APScheduler
│   │   ├── api/v1/              # All endpoint handlers
│   │   ├── models/              # SQLAlchemy ORM models (8 tables)
│   │   ├── schemas/             # Pydantic response models
│   │   ├── services/
│   │   │   ├── index_engine/    # aggregator + index_calc + runner
│   │   │   └── normalizer/      # DTD snapping, fare class mapping
│   │   └── db/                  # SQLAlchemy session + base
│   ├── alembic/                 # Migrations
│   └── requirements.txt
├── scraper/
│   ├── sources/
│   │   ├── amadeus.py           # ✅ Real Amadeus API client
│   │   ├── indigo.py            # STUB
│   │   └── makemytrip.py        # STUB
│   ├── scheduler.py             # APScheduler job
│   └── loader.py                # fare_observations writer
├── data/seed/
│   └── generate_seed.py        # ⚠️ SYNTHETIC DATA — see module docstring
├── frontend/
│   └── src/
│       ├── pages/               # Overview, RouteExplorer, DataQuality, Methodology
│       ├── components/          # Navbar, LoadingSpinner
│       └── api/client.js        # Axios client
├── docs/
│   └── methodology.md
├── docker-compose.yml
└── README.md
```

---

## Team

**Runtime Rulers** — SIH 2026 Problem Statement 26056  
Theme: Travel & Tourism | Category: Software

---

## References

1. MoSPI — CPI 2024 Series (airfare prices via online platforms)
2. UNECE — Consumer Price Index Manual (2020)
3. UNECE — Web Scraping for CPI
4. DGCA — Domestic air traffic statistics (route weighting basis)
5. Amadeus Self-Service API — https://developers.amadeus.com
