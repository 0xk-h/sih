"""
MakeMyTrip Scraper — STUB
=========================
STATUS: NOT IMPLEMENTED — placeholder for future development.

This module will scrape MakeMyTrip flight search results using Playwright.
Left as a stub because:
1. MakeMyTrip uses aggressive anti-bot JS challenges
2. For hackathon MVP, Amadeus API provides reliable real data (scraper/sources/amadeus.py)
3. Full implementation would require: session management, proxy rotation, CAPTCHA handling

To implement:
1. Study MakeMyTrip's flight search URL structure:
   https://www.makemytrip.com/flight/search?itinerary=DEL-BOM-2026-09-01&tripType=O&paxType=A-1_C-0_I-0
2. Use Playwright to wait for the results container
3. Parse fare cards from the rendered DOM
4. Apply normalizer.py for fare class mapping and currency cleanup
5. Respect robots.txt: https://www.makemytrip.com/robots.txt (check before implementing)
6. Rate limit: minimum 5 second delay between requests

See scraper/sources/amadeus.py for the reference implementation pattern.
"""
import logging

logger = logging.getLogger(__name__)


def scrape_makemytrip(origin: str, destination: str, departure_date, dtd_bucket: int) -> list[dict]:
    """
    STUB — Not yet implemented.
    Returns empty list.
    """
    logger.warning(
        "MakeMyTrip scraper is a stub — no data collected for %s→%s. "
        "Use Amadeus API source instead.",
        origin, destination
    )
    return []
