"""
IndiGo Scraper — STUB
======================
STATUS: NOT IMPLEMENTED — placeholder for future development.

IndiGo (goindigo.in) uses heavy JS rendering with anti-bot measures.
For MVP, Amadeus API (scraper/sources/amadeus.py) provides IndiGo fare data
since Amadeus aggregates fares from GDS which includes IndiGo inventory.

To implement a direct scraper:
1. Check robots.txt: https://www.goindigo.in/robots.txt
2. IndiGo search URL: https://www.goindigo.in/flight-booking.html
3. The booking form submits to an internal API; inspect Network tab for XHR calls
4. Use Playwright: await page.goto(url); await page.wait_for_selector('.fare-card')
5. Playwright install: playwright install chromium
6. Rate limit: 10+ seconds between requests, randomized

See scraper/sources/amadeus.py for the reference implementation pattern.
"""
import logging

logger = logging.getLogger(__name__)


def scrape_indigo(origin: str, destination: str, departure_date, dtd_bucket: int) -> list[dict]:
    """
    STUB — Not yet implemented.
    Returns empty list.
    """
    logger.warning(
        "IndiGo direct scraper is a stub — no data collected for %s→%s. "
        "IndiGo fares are available via Amadeus API source.",
        origin, destination
    )
    return []
