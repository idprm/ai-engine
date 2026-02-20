"""Extract addresses from WhatsApp locations and Google Maps links."""
import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from commerce_agent.infrastructure.location.geocoding_client import GeocodingClient

logger = logging.getLogger(__name__)


class LocationExtractor:
    """Extract addresses from WhatsApp locations and Google Maps links.

    Supports:
    - WhatsApp location messages (latitude, longitude, optional address)
    - Google Maps URLs with coordinates
    - Shortened Google Maps URLs (goo.gl/maps/...)

    Usage:
        extractor = LocationExtractor(geocoding_client)

        # From WhatsApp location
        address = await extractor.process_location_message(
            latitude=-6.2088,
            longitude=106.8456,
            address="Jakarta"  # Optional label from WhatsApp
        )

        # From Google Maps URL in text
        url_data = extractor.extract_google_maps_url(
            "Here's my location: https://maps.google.com/?q=-6.2,106.8"
        )

        # Main entry point
        result = await extractor.extract_address_from_message(
            text="Check my location https://maps.google.com/?q=-6.2,106.8",
            location_data={"latitude": -6.2, "longitude": 106.8}
        )
    """

    # Regex patterns for Google Maps URLs
    GOOGLE_MAPS_PATTERNS = [
        # https://maps.google.com/?q=-6.2,106.8
        r"maps\.google\.com\/?\?q=(-?\d+\.?\d*),(-?\d+\.?\d*)",
        # https://www.google.com/maps/@-6.2,106.8,15z
        r"google\.com\/maps\/@(-?\d+\.?\d*),(-?\d+\.?\d*)",
        # https://www.google.com/maps/place/-6.2,106.8
        r"google\.com\/maps\/place\/(-?\d+\.?\d*),(-?\d+\.?\d*)",
        # https://www.google.com/maps?q=-6.2,106.8
        r"google\.com\/maps\?q=(-?\d+\.?\d*),(-?\d+\.?\d*)",
        # https://www.google.com/maps/search/-6.2,106.8
        r"google\.com\/maps\/search\/(-?\d+\.?\d*),(-?\d+\.?\d*)",
        # https://maps.app.goo.gl/abc123 (shortened URL)
        r"maps\.app\.goo\.gl\/[\w]+",
        # https://goo.gl/maps/abc123 (shortened URL)
        r"goo\.gl\/maps\/[\w]+",
    ]

    def __init__(
        self,
        geocoding_client: GeocodingClient | None = None,
        expand_short_urls: bool = True,
    ):
        """Initialize the location extractor.

        Args:
            geocoding_client: Optional GeocodingClient for reverse geocoding.
            expand_short_urls: Whether to expand shortened URLs (goo.gl/maps).
        """
        self._geocoding = geocoding_client
        self._expand_short_urls = expand_short_urls
        self._http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()

    def extract_google_maps_url(self, text: str) -> dict[str, Any] | None:
        """Extract coordinates from Google Maps URL in text.

        Supports various Google Maps URL formats:
        - https://maps.google.com/?q=-6.2,106.8
        - https://www.google.com/maps/@-6.2,106.8,15z
        - https://www.google.com/maps/place/-6.2,106.8
        - https://goo.gl/maps/abc123 (requires expansion)
        - https://maps.app.goo.gl/abc123 (requires expansion)

        Args:
            text: Text that may contain a Google Maps URL.

        Returns:
            Dictionary with latitude, longitude, and URL, or None if not found.
            {
                "latitude": -6.2088,
                "longitude": 106.8456,
                "url": "https://maps.google.com/?q=-6.2,106.8",
                "source": "google_maps_url"
            }
        """
        if not text:
            return None

        # Try each pattern
        for pattern in self.GOOGLE_MAPS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(0)

                # If it's a shortened URL, we'll need to expand it later
                if "goo.gl" in url or "maps.app.goo.gl" in url:
                    return {
                        "url": f"https://{url}",
                        "source": "google_maps_short_url",
                        "needs_expansion": True,
                    }

                # Extract coordinates from the match
                # Pattern groups: (latitude), (longitude)
                if len(match.groups()) >= 2:
                    try:
                        latitude = float(match.group(1))
                        longitude = float(match.group(2))
                        return {
                            "latitude": latitude,
                            "longitude": longitude,
                            "url": f"https://{url}",
                            "source": "google_maps_url",
                        }
                    except (ValueError, IndexError):
                        continue

        return None

    async def expand_short_url(self, url: str) -> str | None:
        """Expand a shortened Google Maps URL.

        Args:
            url: Shortened URL (e.g., https://goo.gl/maps/abc123).

        Returns:
            Expanded URL with coordinates, or None if expansion fails.
        """
        try:
            response = await self._http_client.get(url)
            final_url = str(response.url)

            # Check if the final URL contains coordinates
            if "google.com/maps" in final_url or "maps.google.com" in final_url:
                return final_url

            return None
        except Exception as e:
            logger.error(f"Error expanding short URL {url}: {e}")
            return None

    async def process_location_message(
        self,
        latitude: float,
        longitude: float,
        address: str | None = None,
    ) -> dict[str, Any]:
        """Process location message and return formatted address.

        Args:
            latitude: Latitude coordinate.
            longitude: Longitude coordinate.
            address: Optional address label from WhatsApp.

        Returns:
            Dictionary with address information.
            {
                "latitude": -6.2088,
                "longitude": 106.8456,
                "street": "Jl. Sudirman No. 123",
                "city": "Jakarta",
                "province": "DKI Jakarta",
                "postal_code": "12190",
                "country": "Indonesia",
                "formatted_address": "Jl. Sudirman No. 123, Jakarta, ...",
                "source": "whatsapp_location"
            }
        """
        result = {
            "latitude": latitude,
            "longitude": longitude,
            "source": "whatsapp_location",
            "formatted_address": address,  # Use WhatsApp label as fallback
        }

        # If we have a geocoding client, try to get full address
        if self._geocoding:
            geocoded = await self._geocoding.reverse_geocode(latitude, longitude)
            if geocoded:
                result.update(geocoded)
                result["source"] = "whatsapp_location_geocoded"

        # Build formatted address if not provided
        if not result.get("formatted_address"):
            result["formatted_address"] = self._build_formatted_address(result)

        return result

    async def extract_address_from_message(
        self,
        text: str | None,
        location_data: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Main entry point for extracting address from any message.

        This method handles:
        1. WhatsApp location messages (location_data provided)
        2. Google Maps URLs in text messages
        3. Combination of both

        Args:
            text: Text content of the message (may contain Google Maps URL).
            location_data: WhatsApp location data with latitude/longitude.

        Returns:
            Dictionary with address information, or None if no location found.
            {
                "latitude": -6.2088,
                "longitude": 106.8456,
                "formatted_address": "Jl. Sudirman No. 123, Jakarta, ...",
                "street": "Jl. Sudirman No. 123",
                "city": "Jakarta",
                "province": "DKI Jakarta",
                "postal_code": "12190",
                "country": "Indonesia",
                "source": "whatsapp_location" | "google_maps_url" | ...
            }
        """
        # Priority 1: WhatsApp location message
        if location_data:
            latitude = location_data.get("latitude")
            longitude = location_data.get("longitude")
            address_label = location_data.get("address")

            if latitude is not None and longitude is not None:
                return await self.process_location_message(
                    latitude=float(latitude),
                    longitude=float(longitude),
                    address=address_label,
                )

        # Priority 2: Google Maps URL in text
        if text:
            url_data = self.extract_google_maps_url(text)
            if url_data:
                # Handle shortened URLs
                if url_data.get("needs_expansion"):
                    if self._expand_short_urls:
                        expanded_url = await self.expand_short_url(url_data["url"])
                        if expanded_url:
                            url_data = self.extract_google_maps_url(expanded_url)
                            if not url_data or url_data.get("needs_expansion"):
                                return None
                    else:
                        return None

                latitude = url_data.get("latitude")
                longitude = url_data.get("longitude")

                if latitude is not None and longitude is not None:
                    result = {
                        "latitude": latitude,
                        "longitude": longitude,
                        "source": "google_maps_url",
                    }

                    # Try reverse geocoding
                    if self._geocoding:
                        geocoded = await self._geocoding.reverse_geocode(
                            latitude, longitude
                        )
                        if geocoded:
                            result.update(geocoded)
                            result["source"] = "google_maps_url_geocoded"
                        else:
                            result["formatted_address"] = f"{latitude}, {longitude}"
                    else:
                        result["formatted_address"] = f"{latitude}, {longitude}"

                    return result

        return None

    def _build_formatted_address(self, address_parts: dict[str, Any]) -> str:
        """Build a formatted address string from components.

        Args:
            address_parts: Dictionary with address components.

        Returns:
            Formatted address string.
        """
        parts = []

        if address_parts.get("street"):
            parts.append(address_parts["street"])

        if address_parts.get("city"):
            parts.append(address_parts["city"])

        if address_parts.get("province"):
            parts.append(address_parts["province"])

        if address_parts.get("postal_code"):
            parts.append(address_parts["postal_code"])

        if address_parts.get("country"):
            parts.append(address_parts["country"])

        if parts:
            return ", ".join(parts)

        # Fallback to coordinates
        lat = address_parts.get("latitude", "")
        lng = address_parts.get("longitude", "")
        return f"{lat}, {lng}"
