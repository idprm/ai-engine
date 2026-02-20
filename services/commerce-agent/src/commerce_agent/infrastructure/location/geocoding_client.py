"""Client for reverse geocoding using Google Geocoding API."""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Exception raised when geocoding fails."""
    pass


class GeocodingClient:
    """Client for reverse geocoding using Google Geocoding API.

    Converts latitude/longitude coordinates to readable addresses.

    Usage:
        client = GeocodingClient(api_key="...", base_url="...")
        address = await client.reverse_geocode(-6.2088, 106.8456)
        # Returns: {
        #     "street": "Jl. Sudirman No. 123",
        #     "city": "Jakarta",
        #     "province": "DKI Jakarta",
        #     "postal_code": "12190",
        #     "country": "Indonesia",
        #     "formatted_address": "Jl. Sudirman No. 123, Jakarta, DKI Jakarta 12190, Indonesia"
        # }
    """

    def __init__(self, api_key: str, base_url: str = "https://maps.googleapis.com/maps/api/geocode/json"):
        """Initialize the geocoding client.

        Args:
            api_key: Google Geocoding API key.
            base_url: Google Geocoding API base URL.
        """
        self._api_key = api_key
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        language: str = "id",
    ) -> dict[str, Any] | None:
        """Convert coordinates to address using Google Geocoding API.

        Args:
            latitude: Latitude coordinate.
            longitude: Longitude coordinate.
            language: Language code for results (default: Indonesian).

        Returns:
            Dictionary with address components, or None if geocoding fails.
            {
                "street": "Jl. Sudirman No. 123",
                "city": "Jakarta",
                "province": "DKI Jakarta",
                "postal_code": "12190",
                "country": "Indonesia",
                "formatted_address": "Jl. Sudirman No. 123, Jakarta, DKI Jakarta 12190, Indonesia",
                "latitude": -6.2088,
                "longitude": 106.8456,
            }
        """
        try:
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": self._api_key,
                "language": language,
            }

            response = await self._client.get(self._base_url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "OK":
                logger.warning(f"Geocoding API returned status: {data.get('status')}")
                return None

            results = data.get("results", [])
            if not results:
                logger.warning("No geocoding results found")
                return None

            # Parse the first (most accurate) result
            return self._parse_geocoding_result(results[0], latitude, longitude)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during geocoding: {e}")
            return None
        except Exception as e:
            logger.error(f"Error during geocoding: {e}", exc_info=True)
            return None

    def _parse_geocoding_result(
        self,
        result: dict[str, Any],
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        """Parse Google Geocoding API result into structured address.

        Args:
            result: Single geocoding result from API.
            latitude: Original latitude.
            longitude: Original longitude.

        Returns:
            Structured address dictionary.
        """
        address_components = result.get("address_components", [])
        formatted_address = result.get("formatted_address", "")

        # Initialize address parts
        address = {
            "street": None,
            "city": None,
            "province": None,
            "postal_code": None,
            "country": None,
            "formatted_address": formatted_address,
            "latitude": latitude,
            "longitude": longitude,
        }

        # Map Google address component types to our fields
        type_mapping = {
            "street_number": "street_number",
            "route": "route",
            "sublocality": "sublocality",
            "locality": "city",
            "administrative_area_level_1": "province",
            "administrative_area_level_2": "city",  # Fallback for city
            "postal_code": "postal_code",
            "country": "country",
        }

        # Extra fields for building full street address
        street_number = None
        route = None

        for component in address_components:
            types = component.get("types", [])
            long_name = component.get("long_name", "")

            for comp_type in types:
                if comp_type in type_mapping:
                    field = type_mapping[comp_type]

                    if field == "street_number":
                        street_number = long_name
                    elif field == "route":
                        route = long_name
                    elif field == "city" and not address["city"]:
                        address["city"] = long_name
                    elif field == "province" and not address["province"]:
                        address["province"] = long_name
                    elif field == "postal_code" and not address["postal_code"]:
                        address["postal_code"] = long_name
                    elif field == "country" and not address["country"]:
                        address["country"] = long_name

        # Build street address from components
        if route:
            if street_number:
                address["street"] = f"{route} No. {street_number}"
            else:
                address["street"] = route

        return address
