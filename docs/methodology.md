# Index Methodology — Standalone Reference
**SIH26056 | Real-Time Airfare Price Index for India**

This document is the standalone methodology reference for judges and reviewers. It corresponds to Section 3 of DEVELOPMENT.md.

---

## Problem: Why a Price Index, Not Just Prices?

Airfares change multiple times a day. The question India's CPI needs answered is not "what does a DEL–BOM ticket cost today?" but "**by how much have airfares moved relative to a reference period?**" That's an index — a dimensionless number that tracks movement.

---

## Step 1: Fixing the Comparability Problem (§3.1)

A fare quoted 45 days before departure is not the same product as one quoted 1 day before. They differ systematically: advance fares are typically lower, last-minute fares are typically higher. Mixing them would introduce a structural bias.

**Solution**: Fix **Days-to-Departure (DTD) buckets**. We collect fares at the same booking-window snapshot for each route, every day:

| Bucket | Meaning |
|--------|---------|
| DTD=30 | 30 days before departure |
| DTD=14 | 14 days before departure (advance purchase) |
| DTD=7  | 7 days before departure |
| DTD=1  | 1 day before departure (last-minute) |

**MVP uses DTD=14 and DTD=1** — two buckets is enough to demonstrate the methodology and show the advance vs last-minute price gap.

Each bucket is tracked as its own time series. You never average a DTD=14 fare with a DTD=1 fare.

---

## Step 2: Representative Price per Route/Day (§3.2)

For route *r*, date *t*, DTD bucket *b*, across all airlines and OTAs collected:

```
P(r, t, b) = median(all normalized total fares collected)
```

**Why median, not mean?** Median is robust to outliers — a single mis-parsed fare (e.g., ₹99,000 due to a scraping error) won't shift the representative price. The mean would be pulled significantly. This is standard CPI practice for robust price measurement.

Stored alongside: `min_fare`, `max_fare`, `sample_size` — available via `GET /v1/fares/{route_id}` for auditing.

---

## Step 3: Route-Level Relative (§3.3)

```
I_r(t, b) = [ P(r, t, b) / P(r, base_period, b) ] × 100
```

- Base period = first date with complete coverage across all active routes
- Index = **100 on the base date** by construction
- Moving above 100 means fares have risen relative to base; below 100 means they've fallen

This is directly analogous to a CPI "elementary aggregate" or "item relative."

---

## Step 4: Weighted National Index — Laspeyres Chain-Linked (§3.4)

### Why weight?

DEL–BOM carries ~28% of India's domestic passengers; BOM–GOI carries ~10%. An unweighted average would over-represent thin routes and under-represent busy corridors. We weight routes by their passenger traffic share — exactly how CPI weights "cereals" more heavily than "spices."

### Laspeyres base-weighted aggregate:

```
I(t) = Σ_r [ w_r × I_r(t) ]
```

### Chain-linking (preferred):

```
I(t) = I(t−1) × Σ_r [ w_r(t−1) × P_r(t) / P_r(t−1) ]
```

Chain-linking limits **substitution bias**: if travelers shift away from an expensive route (substitution effect), a fixed-weight index would overstate inflation. Chain-linking allows weights to be updated periodically while maintaining index continuity.

---

## Basket Weights (DGCA FY25)

| Route | Weight | Basis |
|-------|--------|-------|
| DEL–BOM | 0.28 | Busiest domestic corridor |
| DEL–BLR | 0.18 | Major tech hub |
| BOM–BLR | 0.14 | Business corridor |
| DEL–HYD | 0.13 | Significant tech/gov traffic |
| DEL–CCU | 0.12 | East India corridor |
| BOM–GOI | 0.10 | Leisure demand |

Weights derived from DGCA Domestic Air Traffic Statistics FY2024-25. In production, refreshed annually.

---

## Database Audit Trail

Every `fare_observations` row carries:
- `collected_at` — exact timestamp (with timezone) of when the fare was scraped
- `dtd_bucket` — the booking-window bucket (no row exists without one)
- `raw_snapshot_ref` — pointer back to the bronze/raw record for debugging
- `scrape_batch_id` — UUID linking all observations from a single scrape run

This ensures the index is fully reproducible and auditable — you can trace any index value back to the individual fare observations that produced it.

---

## Scope Decisions for MVP

Per the hackathon scoping in DEVELOPMENT.md §10:

| Decision | MVP Choice | Full System |
|----------|------------|-------------|
| Routes | 6 top domestic routes | All DGCA top-30 |
| DTD buckets | 2 (14, 1) | 4 (30, 14, 7, 1) |
| Index formula | Laspeyres chain-linked | + Fisher Ideal for comparison |
| Data sources | Amadeus sandbox API | Full airline/OTA scraping + partnerships |
| History | 60-day synthetic seed | Real-time, continuous |

---

## References

1. UNECE Consumer Price Index Manual (2020) — chain-linking methodology
2. UNECE Web Scraping for CPI — approved collection methods
3. MoSPI CPI 2024 Series — current Indian CPI approach to airfares
4. DGCA Domestic Traffic Statistics — basket weight source
