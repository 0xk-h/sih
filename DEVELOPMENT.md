# Real-Time Airfare Price Index for India — Development Guide
**SIH26056 | Team Runtime Rulers | Theme: Travel & Tourism | Category: Software**

This document is the technical build reference for the prototype: architecture, data schema, scraping design, index methodology, API contracts, dashboard spec, folder layout, and a realistic hackathon build plan.

---

## 1. Problem Restated

Airfares change multiple times a day depending on demand, booking window, and platform. India's CPI needs a reliable way to measure *airfare inflation* — not individual prices, but the **movement** of prices over time. Current CPI airfare collection is periodic and manual-ish; this system automates continuous multi-source collection and turns it into a defensible, standardized index.

**We are building a measurement instrument, not a booking/comparison product.**

---

## 2. System Architecture

```
┌─────────────┐   ┌──────────────┐   ┌────────────────┐   ┌───────────────┐
│  1. COLLECT │──▶│ 2. NORMALIZE │──▶│   3. INDEX      │──▶│  4. DASHBOARD │
│  Scrapers    │   │ Clean, dedupe│   │ Weighted, chain-│   │ React + charts│
│  (Playwright)│   │ standardize  │   │ linked index    │   │ + insights    │
└─────────────┘   └──────────────┘   └────────────────┘   └───────────────┘
```

**Data flow layers (bronze/silver/gold pattern):**
- **Raw layer** — untouched scraped snapshots (for audit/debugging)
- **Cleaned layer** — normalized `fare_observations` (currency, taxes, fare class unified)
- **Aggregated layer** — daily route-level representative price
- **Index layer** — the published index number(s)

---

## 3. Index Methodology (the core technical contribution)

This is the part your deck doesn't specify — and it's the part judges will test you on. Use this.

### 3.1 Fix the comparability problem: booking-window sampling

A fare quoted 45 days before departure and one quoted 1 day before departure are **not the same product**, the same way a "500g pack of rice" and a "5kg pack" aren't the same CPI item. CPI methodology fixes item specifications; we do the equivalent by fixing **days-to-departure (DTD) buckets**.

Collect fares at fixed DTD checkpoints for every route, every day:
- DTD 30 (a month out)
- DTD 14
- DTD 7
- DTD 1 (near-term/last-minute)

Each bucket is tracked as its **own time series**. This directly neutralizes the "index may be biased by scrape timing" risk from your feasibility slide.

### 3.2 Representative price per route/day

For route *r*, date *t*, DTD bucket *b*, across all airlines/OTAs collected that day:

```
P(r, t, b) = median(all normalized total fares collected)
```

Use **median**, not mean — it's robust to scraping outliers (a single mis-parsed fare won't distort the series). Store min/max/sample size alongside it for data-quality auditing.

### 3.3 Route-level relative (like a CPI item relative)

```
I_r(t) = [ P(r, t) / P(r, base_period) ] × 100
```

### 3.4 Aggregate index — weighted, chain-linked (Laspeyres-type / Fisher option)

Routes don't matter equally — DEL–BOM carries far more passengers than a thin regional route, so it should move the index more, exactly like CPI weights "cereals" heavier than "spices."

**Weights**: derive `w_r` from route passenger-traffic share (DGCA domestic traffic statistics, publicly published) — this is your basket weight, refreshed periodically (e.g., yearly), not per scrape.

**Base-weighted (Laspeyres) index:**
```
I(t) = Σ_r [ w_r × I_r(t) ]
```

**Chain-linking** (recommended for a multi-month demo, and standard CPI practice to limit substitution bias):
```
I(t) = I(t−1) × Σ_r [ w_r(t−1) × P_r(t) / P_r(t−1) ]
```

**Stretch goal**: compute a **Fisher Ideal Index** (geometric mean of Laspeyres and Paasche) — more defensible, easy talking point ("we didn't just pick the simplest formula, we tested robustness against substitution bias") if you have time to implement both.

### 3.5 Sampling frame (routes to cover)

Don't try to cover all of India — pick the **top N domestic routes by passenger volume** (DGCA data), which typically account for the large majority of domestic traffic. For the prototype: **6–10 routes** is enough to demonstrate a credible weighted index (e.g., DEL–BOM, DEL–BLR, BOM–BLR, DEL–HYD, DEL–CCU, BOM–GOI, DEL–MAA, BLR–HYD).

---

## 4. Data Sources & Ethical/Legal Scraping Notes

**Sources:**
- **Airline direct sites**: IndiGo, Air India, SpiceJet, Akasa Air, Air India Express
- **OTAs**: MakeMyTrip, Yatra, Cleartrip, EaseMyTrip, ixigo

**Practical guidance (important for judges' Q&A on legality):**
- Respect `robots.txt` and each site's Terms of Service; scrape only publicly displayed fare-search results, never authenticated/account areas.
- Rate-limit aggressively (seconds between requests, randomized delay) — this is both an ethical requirement and a technical necessity to avoid getting blocked.
- Cache results; never re-scrape data you already have for that DTD/date/route combination.
- For a **production-grade** system, the sustainable path is official data partnerships/APIs (e.g., Amadeus Self-Service API, aviation fare aggregator APIs) rather than scraping at scale — mention this explicitly as your "path to production" in Q&A. It shows you understand scraping is a bridge technique, not a permanent architecture.
- For the **hackathon demo**, it's reasonable to: (a) do a small number of *live* scrape calls on stage to prove the collector works, and (b) pre-seed a synthetic/historical time series (generated with realistic randomness around real observed fares) so the index dashboard can show a believable multi-week trend without needing weeks of real runtime. Say this openly — it's honest and judges respect it.

---

## 5. Database Schema (PostgreSQL)

```sql
CREATE TABLE airports (
  airport_id SERIAL PRIMARY KEY,
  iata_code CHAR(3) UNIQUE NOT NULL,
  city TEXT, state TEXT
);

CREATE TABLE airlines (
  airline_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  iata_code CHAR(2)
);

CREATE TABLE sources (
  source_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,              -- e.g. 'MakeMyTrip', 'IndiGo Direct'
  source_type TEXT NOT NULL,       -- 'airline_direct' | 'ota'
  base_url TEXT
);

CREATE TABLE routes (
  route_id SERIAL PRIMARY KEY,
  origin_airport_id INT REFERENCES airports(airport_id),
  dest_airport_id INT REFERENCES airports(airport_id),
  distance_km NUMERIC
);

CREATE TABLE route_weights (
  route_id INT REFERENCES routes(route_id),
  weight NUMERIC NOT NULL,         -- basket weight, sums to 1 across active routes
  weight_source TEXT,              -- e.g. 'DGCA FY25 traffic share'
  effective_from DATE,
  PRIMARY KEY (route_id, effective_from)
);

CREATE TABLE fare_observations (       -- "silver" cleaned layer
  obs_id BIGSERIAL PRIMARY KEY,
  route_id INT REFERENCES routes(route_id),
  airline_id INT REFERENCES airlines(airline_id),
  source_id INT REFERENCES sources(source_id),
  departure_date DATE NOT NULL,
  days_to_departure INT NOT NULL,
  dtd_bucket INT NOT NULL,          -- snapped to 30/14/7/1
  fare_class TEXT,                  -- normalized: 'economy' | 'premium_economy' | 'business'
  base_fare NUMERIC,
  taxes_fees NUMERIC,
  total_fare NUMERIC NOT NULL,
  currency CHAR(3) DEFAULT 'INR',
  collected_at TIMESTAMPTZ NOT NULL,
  scrape_batch_id UUID,
  raw_snapshot_ref TEXT             -- pointer to raw/bronze record for audit
);

CREATE TABLE daily_route_price (      -- "gold" aggregated layer
  route_id INT REFERENCES routes(route_id),
  price_date DATE NOT NULL,
  dtd_bucket INT NOT NULL,
  median_fare NUMERIC,
  min_fare NUMERIC,
  max_fare NUMERIC,
  sample_size INT,
  PRIMARY KEY (route_id, price_date, dtd_bucket)
);

CREATE TABLE index_values (
  index_id BIGSERIAL PRIMARY KEY,
  index_date DATE NOT NULL,
  index_scope TEXT NOT NULL,        -- 'national' | 'route' | 'regional'
  scope_ref INT,                    -- route_id if scope='route', else null
  dtd_bucket INT,
  value NUMERIC NOT NULL,
  base_period DATE,
  methodology_version TEXT
);
```

Add unique constraints / dedup keys on `(route_id, airline_id, source_id, departure_date, dtd_bucket, fare_class, date_trunc('hour', collected_at))` to prevent duplicate observations from retried scrape jobs.

---

## 6. Backend API (FastAPI)

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | liveness check |
| `GET` | `/routes` | list tracked routes + current weights |
| `GET` | `/fares/{route_id}?dtd=&from=&to=` | raw/cleaned fare series for a route |
| `GET` | `/index/national?from=&to=&dtd=` | headline index time series |
| `GET` | `/index/route/{route_id}?from=&to=` | route-level index |
| `GET` | `/dashboard/summary` | latest index value, MoM/YoY change, top movers |
| `POST` | `/scrape/trigger` | manually trigger a scrape batch (demo control) |
| `GET` | `/data-quality` | sample sizes, last scrape times, missing coverage |

Use Pydantic response models; version the API (`/v1/...`) since `methodology_version` will change as you refine the index formula.

---

## 7. Scraping & ETL Pipeline

```
scraper/
  sources/
    indigo.py          # one module per source, isolates site-specific parsing
    makemytrip.py
    ...
  scheduler.py          # APScheduler (simplest for hackathon) triggers jobs per route × source × DTD bucket
  normalizer.py          # currency, tax/fee split, fare-class mapping, DTD snapping
  dedup.py
  loader.py              # writes to raw + fare_observations
```

- **Scheduler**: `APScheduler` is enough for a prototype (no need for Airflow/Celery at this scale). Run every N hours per route/source.
- **Collector**: Playwright preferred over Selenium for speed and built-in waiting; fall back to `requests` + `BeautifulSoup` for any source that exposes fare data via a plain HTML response or a public JSON endpoint used by their own frontend.
- **Normalizer rules**:
  - Strip currency symbols, convert to INR if needed
  - Split total fare into `base_fare` + `taxes_fees` where the source shows a breakdown; else store total only
  - Map site-specific fare names ("Saver", "Flexi", "SpiceMax", etc.) to a **standard 3-tier bucket**: economy / premium_economy / business
  - Snap actual days-to-departure to nearest DTD bucket (30/14/7/1)
- **Dedup**: hash `(route, airline, source, departure_date, dtd_bucket, fare_class, hour(collected_at))`; skip insert on collision.

---

## 8. Index Computation Module (Pandas)

Pseudocode for the daily job that turns `fare_observations` → `daily_route_price` → `index_values`:

```python
# 1. Aggregate to daily route price
daily = (
    fare_obs_df
    .groupby(["route_id", "departure_date", "dtd_bucket"])
    .agg(median_fare=("total_fare", "median"),
         min_fare=("total_fare", "min"),
         max_fare=("total_fare", "max"),
         sample_size=("total_fare", "count"))
)

# 2. Route relative vs base period
route_relative = daily["median_fare"] / base_period_price[route_id] * 100

# 3. Weighted aggregate (Laspeyres, chain-linked)
index_t = sum(weight[route_id] * relative_change[route_id] for route_id in active_routes)
index_today = index_yesterday * index_t
```

Use `Pandas` for the pipeline, `Scikit-learn`/`statsmodels` for the analytics layer on top:
- **Seasonal decomposition** (trend/seasonal/residual) to show festival-season fare spikes
- **Z-score anomaly flagging** on `fare_observations` to catch scraper parsing errors before they pollute the index
- **Simple forecast** (linear trend or moving average) for a "projected next 30 days" chart — good demo material, keep the model simple and explainable rather than a black box.

---

## 9. Frontend Dashboard (React + Chart.js)

| Page | Contents |
|---|---|
| **Overview** | Headline national index value, MoM/YoY % change, trend line |
| **Route Explorer** | Select a route → price trend by DTD bucket, seasonal pattern |
| **Source Comparison** | Airline-direct vs OTA price gap over time |
| **Data Quality** | Sample sizes, last scrape timestamps, coverage gaps (builds trust — CPI-adjacent tools need to show their work) |
| **Methodology** | Plain-language explanation of the index formula, base period, and current weights — transparency is part of the pitch, not an afterthought |

---

## 10. Suggested Hackathon MVP Scope

Given typical hackathon time constraints, don't try to build the full system — build a **convincing vertical slice**:

- **6–8 routes**, 2–3 airlines, 2 OTAs
- **2 DTD buckets** (e.g., 14 and 1) instead of all 4 — halves scraping/normalization work
- **Live scrape demo** for 1–2 routes on stage (proves the collector genuinely works)
- **Seeded synthetic historical series** (30–60 days, generated with realistic noise around a handful of real scraped anchor points) to populate the dashboard trend charts — say this openly when presenting
- **Laspeyres-only** index (skip Fisher unless time allows) with fixed DGCA-derived weights
- **Dashboard**: Overview + Route Explorer pages are the priority; Data Quality and Methodology pages if time permits

### Rough build order
1. Schema + FastAPI skeleton + Postgres running (Docker)
2. One working scraper end-to-end (1 airline + 1 OTA) → prove the pipeline
3. Normalizer + index calculation on seeded data
4. Dashboard wired to `/index/national` and `/index/route/{id}`
5. Add remaining routes/sources, polish, prep the live-demo script
6. Buffer time for the pitch deck/video and Q&A rehearsal (methodology questions are the likely curveball — know Section 3 cold)

---

## 11. Folder Structure

```
airfare-index/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/            # route handlers
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/
│   │   │   ├── index_engine/
│   │   │   └── normalizer/
│   │   └── db/
│   └── requirements.txt
├── scraper/
│   ├── sources/
│   └── scheduler.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── charts/
│   └── package.json
├── data/
│   └── seed/                # synthetic historical seed generator
├── docs/
│   └── methodology.md       # Section 3 of this doc, standalone for judges
├── docker-compose.yml
└── README.md
```

---

## 12. Local Setup

```bash
# Backend
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary pandas scikit-learn playwright apscheduler
playwright install

# Database
docker compose up -d postgres

# Frontend
cd frontend && npm install && npm run dev
```

`docker-compose.yml` should bring up Postgres at minimum; add the backend/frontend as services once containerized.

---

## 13. Risks & Mitigations (expanded from the deck)

| Risk | Mitigation | Implementation detail |
|---|---|---|
| Prices change constantly | Timestamp every observation | `collected_at` on every row, DTD-bucket snapping |
| Website access limits | Permitted sources, controlled rate | APScheduler with jittered delays, robots.txt compliance |
| Fare format differences | Standardize taxes/fees/class | `normalizer.py` mapping tables |
| Missing/duplicate data | Validate + dedupe | Hash-based dedup key, sample-size tracking in `daily_route_price` |
| Index bias | Route-wise weighting, validation | DGCA traffic-share weights, Laspeyres/Fisher comparison |
| Comparability across booking windows | Fixed DTD buckets | Section 3.1 |

---

## 14. Glossary

- **CPI** – Consumer Price Index
- **OTA** – Online Travel Agency
- **MoSPI** – Ministry of Statistics and Programme Implementation
- **UNECE** – United Nations Economic Commission for Europe
- **DTD** – Days to Departure
- **DGCA** – Directorate General of Civil Aviation (source for route traffic-share weights)

---

## 15. References

1. MoSPI — CPI 2024 Series (airfare prices collected via online platforms)
2. UNECE — Consumer Price Index Manual (2020)
3. UNECE — Web Scraping for CPI
4. UNECE — CPI Expert Group: New Data Sources
5. UNECE — Price Indices Resources
6. DGCA — Domestic air traffic statistics (for route weighting)
