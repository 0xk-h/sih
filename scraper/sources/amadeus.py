"""
Amadeus Flight Offers API — Real Data Source
============================================
Uses the Amadeus Self-Service API (sandbox tier) to fetch flight offers
for a given origin, destination, and departure date.

Amadeus sandbox: https://developers.amadeus.com/self-service
- Free tier, no real booking data, but realistic fare structures
- Must register at https://developers.amadeus.com and get API keys

This is the "real" data source for the MVP as discussed in the plan.
Rate limits: Amadeus sandbox allows ~500 req/day on free tier.
"""
import httpx
import logging
from datetime import date, datetime, timezone
from typing import Optional
import os
import sys

logger = logging.getLogger(__name__)

AMADEUS_BASE_URL = os.environ.get("AMADEUS_BASE_URL", "https://test.api.amadeus.com")
AMADEUS_CLIENT_ID = os.environ.get("AMADEUS_CLIENT_ID", "")
AMADEUS_CLIENT_SECRET = os.environ.get("AMADEUS_CLIENT_SECRET", "")

# Rate limiting: wait between requests (be conservative)
REQUEST_DELAY_SECONDS = 2.0


class AmadeusClient:
    """Thin client for Amadeus Flight Offers Price API."""

    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def _get_token(self) -> str:
        """Fetch or refresh OAuth2 client credentials token."""
        now = datetime.now(timezone.utc)
        if self._access_token and self._token_expiry and now < self._token_expiry:
            return self._access_token

        resp = httpx.post(
            f"{AMADEUS_BASE_URL}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": AMADEUS_CLIENT_ID,
                "client_secret": AMADEUS_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        resp.raise_for_status()
        token_data = resp.json()
        self._access_token = token_data["access_token"]
        # Amadeus tokens expire in 1799 seconds; subtract 60s buffer
        self._token_expiry = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + token_data.get("expires_in", 1799) - 60,
            tz=timezone.utc,
        )
        logger.info("Amadeus token obtained, expires at %s", self._token_expiry)
        return self._access_token

    def get_flight_offers(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        adults: int = 1,
        travel_class: str = "ECONOMY",
        max_results: int = 10,
    ) -> list[dict]:
        """
        Fetch flight offers for a route on a given date.
        Returns list of normalized fare dicts.

        Respects robots.txt (Amadeus API does not have a robots.txt restriction;
        use is governed by ToS which explicitly allows fare lookups).
        Rate-limited to REQUEST_DELAY_SECONDS between calls.
        """
        if not AMADEUS_CLIENT_ID or not AMADEUS_CLIENT_SECRET:
            logger.warning(
                "Amadeus credentials not configured. "
                "Set AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in .env"
            )
            return []

        try:
            token = self._get_token()
        except Exception as e:
            logger.error("Failed to get Amadeus token: %s", e)
            return []

        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date.isoformat(),
            "adults": adults,
            "travelClass": travel_class,
            "max": max_results,
            "currencyCode": "INR",
            "nonStop": "false",
        }

        try:
            import time
            time.sleep(REQUEST_DELAY_SECONDS)  # Rate limiting

            resp = httpx.get(
                f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Amadeus API error %d for %s→%s on %s: %s",
                e.response.status_code, origin, destination, departure_date, e.response.text
            )
            return []
        except Exception as e:
            logger.error("Amadeus request failed: %s", e)
            return []

        offers = data.get("data", [])
        logger.info(
            "Amadeus returned %d offers for %s→%s on %s",
            len(offers), origin, destination, departure_date
        )

        return self._parse_offers(offers, origin, destination, departure_date)

    def _parse_offers(
        self,
        offers: list[dict],
        origin: str,
        destination: str,
        departure_date: date,
    ) -> list[dict]:
        """Parse Amadeus flight offer objects into normalized fare dicts."""
        parsed = []
        for offer in offers:
            try:
                price = offer.get("price", {})
                total = float(price.get("grandTotal") or price.get("total", 0))
                base = float(price.get("base", total * 0.82))
                taxes = round(total - base, 2)

                # Carrier code from first itinerary's first segment
                itineraries = offer.get("itineraries", [{}])
                segments = itineraries[0].get("segments", [{}]) if itineraries else [{}]
                carrier_code = segments[0].get("carrierCode", "") if segments else ""

                # Cabin class
                traveler_pricings = offer.get("travelerPricings", [{}])
                cabin = "economy"
                if traveler_pricings:
                    fare_details = traveler_pricings[0].get("fareDetailsBySegment", [{}])
                    if fare_details:
                        raw_cabin = fare_details[0].get("cabin", "ECONOMY").lower()
                        cabin_map = {
                            "economy": "economy",
                            "premium_economy": "premium_economy",
                            "business": "business",
                            "first": "business",
                        }
                        cabin = cabin_map.get(raw_cabin, "economy")

                parsed.append({
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                    "carrier_iata": carrier_code,
                    "fare_class": cabin,
                    "total_fare": total,
                    "base_fare": base,
                    "taxes_fees": taxes,
                    "currency": "INR",
                    "collected_at": datetime.now(timezone.utc),
                    "source_name": "Amadeus Test API",
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.warning("Failed to parse offer: %s — %s", offer, e)
                continue

        return parsed


# Module-level singleton
_client: Optional[AmadeusClient] = None


def get_amadeus_client() -> AmadeusClient:
    global _client
    if _client is None:
        _client = AmadeusClient()
    return _client
