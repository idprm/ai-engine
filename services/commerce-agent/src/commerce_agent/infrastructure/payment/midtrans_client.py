"""Midtrans payment gateway client."""
import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MidtransClient:
    """Client for Midtrans payment gateway API.

    Supports:
    - Bank transfer (virtual accounts)
    - E-wallets (GoPay, ShopeePay)
    - QRIS
    - Credit cards
    """

    SANDBOX_BASE_URL = "https://api.sandbox.midtrans.com"
    PRODUCTION_BASE_URL = "https://api.midtrans.com"

    def __init__(
        self,
        server_key: str,
        client_key: str,
        is_production: bool = False,
    ):
        """Initialize Midtrans client.

        Args:
            server_key: Midtrans server key.
            client_key: Midtrans client key.
            is_production: Use production environment.
        """
        self._server_key = server_key
        self._client_key = client_key
        self._base_url = self.PRODUCTION_BASE_URL if is_production else self.SANDBOX_BASE_URL
        self._http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()

    def _get_auth_header(self) -> str:
        """Get Basic Auth header value."""
        auth_string = base64.b64encode(f"{self._server_key}:".encode()).decode()
        return f"Basic {auth_string}"

    async def create_transaction(
        self,
        order_id: str,
        amount: float,
        customer_email: str | None = None,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        payment_type: str = "bank_transfer",
        item_details: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Create a payment transaction.

        Args:
            order_id: Unique order identifier.
            amount: Transaction amount.
            customer_email: Customer email.
            customer_name: Customer name.
            customer_phone: Customer phone.
            payment_type: Payment method type.
            item_details: List of item details.

        Returns:
            Transaction details including payment URL/QR code.
        """
        url = f"{self._base_url}/v2/charge"

        # Build transaction payload
        gross_amount = int(amount)  # Midtrans expects integer

        payload = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": gross_amount,
            },
            "customer_details": {},
        }

        if customer_email:
            payload["customer_details"]["email"] = customer_email
        if customer_name:
            payload["customer_details"]["first_name"] = customer_name
        if customer_phone:
            payload["customer_details"]["phone"] = customer_phone

        if item_details:
            payload["item_details"] = item_details

        # Set payment type specific options
        if payment_type == "bank_transfer":
            payload["payment_type"] = "bank_transfer"
            payload["bank_transfer"] = {"bank": "bca"}

        elif payment_type == "ewallet":
            payload["payment_type"] = "gopay"
            payload["gopay"] = {"enable_callback": True}

        elif payment_type == "qris":
            payload["payment_type"] = "qris"
            payload["qris"] = {"acquirer": "gopay"}

        else:
            # Default to bank transfer
            payload["payment_type"] = "bank_transfer"
            payload["bank_transfer"] = {"bank": "bca"}

        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = await self._http_client.post(
            url,
            headers=headers,
            content=json.dumps(payload),
        )

        if response.status_code != 201:
            logger.error(f"Midtrans create transaction failed: {response.text}")
            raise Exception(f"Failed to create transaction: {response.text}")

        result = response.json()

        # Extract relevant info
        transaction_id = result.get("transaction_id", order_id)
        payment_type_result = result.get("payment_type", payment_type)

        # Get payment URL or VA number
        payment_url = None
        va_number = None
        qr_string = None

        if payment_type == "bank_transfer":
            va_numbers = result.get("va_numbers", [])
            if va_numbers:
                va_number = va_numbers[0].get("va_number")

        elif payment_type == "qris":
            actions = result.get("actions", [])
            for action in actions:
                if action.get("name") == "generate-qr-code":
                    qr_string = action.get("url")

        # Get action URLs
        actions = result.get("actions", [])
        for action in actions:
            if action.get("name") == "deeplink-redirect":
                payment_url = action.get("url")

        return {
            "transaction_id": transaction_id,
            "order_id": order_id,
            "payment_type": payment_type_result,
            "gross_amount": gross_amount,
            "payment_url": payment_url,
            "va_number": va_number,
            "qr_string": qr_string,
            "expiry_time": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "status": result.get("transaction_status", "pending"),
        }

    async def check_transaction_status(self, order_id: str) -> dict[str, Any]:
        """Check transaction status.

        Args:
            order_id: Order ID or transaction ID.

        Returns:
            Transaction status details.
        """
        url = f"{self._base_url}/v2/{order_id}/status"

        headers = {
            "Authorization": self._get_auth_header(),
            "Accept": "application/json",
        }

        response = await self._http_client.get(url, headers=headers)

        if response.status_code != 200:
            logger.error(f"Midtrans status check failed: {response.text}")
            raise Exception(f"Failed to check status: {response.text}")

        result = response.json()

        return {
            "transaction_id": result.get("transaction_id"),
            "order_id": result.get("order_id"),
            "transaction_status": result.get("transaction_status"),
            "payment_type": result.get("payment_type"),
            "gross_amount": result.get("gross_amount"),
            "transaction_time": result.get("transaction_time"),
            "settlement_time": result.get("settlement_time"),
        }

    async def cancel_transaction(self, order_id: str) -> dict[str, Any]:
        """Cancel a transaction.

        Args:
            order_id: Order ID to cancel.

        Returns:
            Cancellation result.
        """
        url = f"{self._base_url}/v2/{order_id}/cancel"

        headers = {
            "Authorization": self._get_auth_header(),
            "Accept": "application/json",
        }

        response = await self._http_client.post(url, headers=headers)

        if response.status_code not in [200, 201, 412]:
            logger.error(f"Midtrans cancel failed: {response.text}")
            raise Exception(f"Failed to cancel: {response.text}")

        result = response.json()

        return {
            "transaction_id": result.get("transaction_id"),
            "order_id": result.get("order_id"),
            "status": result.get("status"),
            "message": result.get("status_message"),
        }

    def verify_webhook_signature(
        self,
        order_id: str,
        status_code: str,
        gross_amount: str,
        signature_key: str,
    ) -> bool:
        """Verify webhook signature.

        Args:
            order_id: Order ID from webhook.
            status_code: Status code from webhook.
            gross_amount: Gross amount from webhook.
            signature_key: Signature key from webhook.

        Returns:
            True if signature is valid.
        """
        expected = hashlib.sha512(
            f"{order_id}{status_code}{gross_amount}{self._server_key}".encode()
        ).hexdigest()

        return hmac.compare_digest(expected, signature_key)
