"""
Normalizer — converts raw scraped fares to the standard silver-layer format.
Applied by scrapers before inserting into fare_observations.
"""
from datetime import date

# ── DTD bucket snapping ─────────────────────────────────────────────────────
# MVP uses only 14 and 1 (per DEVELOPMENT.md §10)
DTD_BUCKETS_MVP = [14, 1]
DTD_ALL = [30, 14, 7, 1]


def snap_dtd_to_bucket(days_to_departure: int, buckets: list[int] = DTD_BUCKETS_MVP) -> int:
    """
    Snap actual days-to-departure to the nearest DTD bucket.
    E.g. dtd=16 → bucket 14, dtd=3 → bucket 1.
    """
    if not buckets:
        raise ValueError("buckets list is empty")
    return min(buckets, key=lambda b: abs(b - days_to_departure))


# ── Fare class mapping ──────────────────────────────────────────────────────
# Map airline/OTA-specific fare names → standard 3-tier bucket
FARE_CLASS_MAP: dict[str, str] = {
    # Economy variants
    "saver": "economy",
    "lite": "economy",
    "value": "economy",
    "smart saver": "economy",
    "indigo saver": "economy",
    "economy": "economy",
    "eco": "economy",
    "regular": "economy",
    "flexi standard": "economy",
    "standard": "economy",
    # Premium economy
    "premium economy": "premium_economy",
    "premiumeconomy": "premium_economy",
    "comfort": "premium_economy",
    "spicemax": "premium_economy",
    "flexi plus": "premium_economy",
    "flexiplus": "premium_economy",
    # Business
    "business": "business",
    "first": "business",
    "club class": "business",
    "maharaja class": "business",
    "air india business": "business",
    "flexi": "business",  # treat Flexi as business-equivalent for some carriers
}


def normalize_fare_class(raw_class: str | None) -> str:
    """Normalize raw fare class name to standard 3-tier bucket."""
    if not raw_class:
        return "economy"
    return FARE_CLASS_MAP.get(raw_class.strip().lower(), "economy")


# ── Currency normalization ──────────────────────────────────────────────────
def normalize_currency(amount: float | None, currency: str = "INR") -> float | None:
    """
    For MVP all sources report INR; this is a stub for future multi-currency support.
    """
    if amount is None:
        return None
    if currency == "INR":
        return round(float(amount), 2)
    # TODO: Add FX conversion when non-INR sources are added
    raise ValueError(f"Non-INR currency not yet supported: {currency}")


# ── Fare parsing utilities ──────────────────────────────────────────────────
def parse_fare_string(fare_str: str) -> float | None:
    """
    Strip currency symbols, commas, whitespace and parse to float.
    Handles formats: '₹4,500', 'INR 4500.00', '4,500.50'
    """
    if not fare_str:
        return None
    cleaned = (
        fare_str.replace("₹", "")
        .replace("INR", "")
        .replace(",", "")
        .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return None
