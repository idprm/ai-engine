"""Xendit payment gateway client."""
import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class XenditClient:
    """Client for Xendit payment gateway API.

    Supports:
    - Virtual accounts (bank transfer)
    - E-wallets (OVO, Dana, LinkAja)
    - QRIS
    - Payment links
    """

    BASE_URL = "https://api.xendit.co"

    def __init__(
        self,
        secret_key: str,
        public_key: str | None = None,
    ):
        """Initialize Xendit client.

        Args:
            secret_key: Xendit secret API key.
            public_key: Xendit public API key (for some operations).
        """
        self._secret_key = secret_key
        self._public_key = public_key
        self._http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()

    def _get_auth_header(self) -> str:
        """Get Basic Auth header value."""
        auth_string = base64.b64encode(f"{self._secret_key}:".encode()).decode()
        return f"Basic {auth_string}"

    async def create_invoice(
        self,
        external_id: str,
        amount: float,
        customer_email: str | None = None,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        description: str | None = None,
        invoice_duration: int = 86400,  # 24 hours in seconds
    ) -> dict[str, Any]:
        """Create a payment invoice (payment link).

        Args:
            external_id: Unique external identifier (order ID).
            amount: Invoice amount.
            customer_email: Customer email.
            customer_name: Customer name.
            customer_phone: Customer phone.
            description: Invoice description.
            invoice_duration: Invoice validity duration in seconds.

        Returns:
            Invoice details including payment URL.
        """
        url = f"{self.BASE_URL}/v2/invoices"

        payload = {
            "external_id": external_id,
            "amount": int(amount),
            "invoice_duration": invoice_duration,
        }

        if customer_email:
            payload["payer_email"] = customer_email
        if customer_name:
            payload["customer"] = {
                "given_names": customer_name,
                "email": customer_email,
                "mobile_number": customer_phone,
            }
        if description:
            payload["description"] = description

        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
        }

        response = await self._http_client.post(
            url,
            headers=headers,
            content=json.dumps(payload),
        )

        if response.status_code != 200 and response.status_code != 201:
            logger.error(f"Xendit create invoice failed: {response.text}")
            raise Exception(f"Failed to create invoice: {response.text}")

        result = response.json()

        return {
            "transaction_id": result.get("id"),
            "external_id": result.get("external_id"),
            "invoice_url": result.get("invoice_url"),
            "amount": result.get("amount"),
            "status": result.get("status"),
            "expiry_date": result.get("expiry_date"),
            "created_at": result.get("created"),
        }

    async def create_virtual_account(
        self,
        external_id: str,
        amount: float,
        bank_code: str = "BCA",
        customer_name: str | None = None,
        expiration_minutes: int = 1440,  # 24 hours
    ) -> dict[str, Any]:
        """Create a virtual account for bank transfer.

        Args:
            external_id: Unique external identifier.
            amount: Expected amount.
            bank_code: Bank code (BCA, BNI, BRI, MANDIRI, etc.).
            customer_name: Customer name for VA.
            expiration_minutes: VA validity in minutes.

        Returns:
            Virtual account details.
        """
        url = f"{self.BASE_URL}/callback_virtual_accounts"

        payload = {
            "external_id": external_id,
            "bank_code": bank_code,
            "name": customer_name or "Customer",
            "is_closed": True,
            "expected_amount": int(amount),
            "expiration_date": (
                datetime.utcnow() + timedelta(minutes=expiration_minutes)
            ).isoformat(),
        }

        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
        }

        response = await self._http_client.post(
            url,
            headers=headers,
            content=json.dumps(payload),
        )

        if response.status_code != 200 and response.status_code != 201:
            logger.error(f"Xendit create VA failed: {response.text}")
            raise Exception(f"Failed to create VA: {response.text}")

        result = response.json()

        return {
            "transaction_id": result.get("id"),
            "external_id": result.get("external_id"),
            "account_number": result.get("account_number"),
            "bank_code": result.get("bank_code"),
            "name": result.get("name"),
            "amount": result.get("expected_amount"),
            "expiration_date": result.get("expiration_date"),
            "status": "PENDING",
        }

    async def create_ewallet_charge(
        self,
        reference_id: str,
        amount: float,
        currency: str = "IDR",
        checkout_method: str = "ONE_TIME_PAYMENT",
        ewallet_type: str = "OVO",
        customer_phone: str | None = None,
    ) -> dict[str, Any]:
        """Create an e-wallet charge.

        Args:
            reference_id: Unique reference ID.
            amount: Charge amount.
            currency: Currency code.
            checkout_method: Checkout method.
            ewallet_type: E-wallet type (OVO, DANA, LINKAJA, SHOPEEPAY).
            customer_phone: Customer phone for OVO.

        Returns:
            Charge details including checkout URL.
        """
        url = f"{self.BASE_URL}/ewallets/charges"

        payload = {
            "reference_id": reference_id,
            "currency": currency,
            "amount": int(amount),
            "checkout_method": checkout_method,
            "channel_code": f"ID_{ewallet_type}",
        }

        if ewallet_type == "OVO" and customer_phone:
            payload["channel_properties"] = {
                "mobile_number": customer_phone,
            }

        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
        }

        response = await self._http_client.post(
            url,
            headers=headers,
            content=json.dumps(payload),
        )

        if response.status_code != 200 and response.status_code != 201:
            logger.error(f"Xendit e-wallet charge failed: {response.text}")
            raise Exception(f"Failed to create e-wallet charge: {response.text}")

        result = response.json()

        return {
            "transaction_id": result.get("id"),
            "reference_id": result.get("reference_id"),
            "status": result.get("status"),
            "checkout_url": result.get("actions", {}).get("desktop_web_checkout_url"),
            "amount": result.get("charge_amount"),
            "ewallet_type": ewallet_type,
        }

    async def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        """Get invoice details.

        Args:
            invoice_id: Invoice ID.

        Returns:
            Invoice details.
        """
        url = f"{self.BASE_URL}/v2/invoices/{invoice_id}"

        headers = {
            "Authorization": self._get_auth_header(),
        }

        response = await self._http_client.get(url, headers=headers)

        if response.status_code != 200:
            logger.error(f"Xendit get invoice failed: {response.text}")
            raise Exception(f"Failed to get invoice: {response.text}")

        result = response.json()

        return {
            "transaction_id": result.get("id"),
            "external_id": result.get("external_id"),
            "status": result.get("status"),
            "amount": result.get("amount"),
            "paid_at": result.get("paid_at"),
            "expiry_date": result.get("expiry_date"),
        }

    async def check_transaction_status(self, transaction_id: str) -> dict[str, Any]:
        """Check transaction status.

        This checks the invoice status as a general method.

        Args:
            transaction_id: Transaction/invoice ID.

        Returns:
            Transaction status.
        """
        try:
            return await self.get_invoice(transaction_id)
        except Exception:
            # Fallback to VA status or other methods
            return {
                "transaction_id": transaction_id,
                "status": "UNKNOWN",
                "message": "Could not determine status",
            }

    async def expire_invoice(self, invoice_id: str) -> dict[str, Any]:
        """Expire an invoice manually.

        Args:
            invoice_id: Invoice ID to expire.

        Returns:
            Result of expiration.
        """
        url = f"{self.BASE_URL}/invoices/{invoice_id}/expire!"

        headers = {
            "Authorization": self._get_auth_header(),
        }

        response = await self._http_client.post(url, headers=headers)

        if response.status_code not in [200, 201]:
            logger.error(f"Xendit expire invoice failed: {response.text}")
            raise Exception(f"Failed to expire invoice: {response.text}")

        result = response.json()

        return {
            "transaction_id": result.get("id"),
            "status": result.get("status"),
            "message": "Invoice expired",
        }

    def verify_webhook_signature(
        self,
        callback_token: str,
        expected_token: str,
    ) -> bool:
        """Verify webhook callback token.

        Args:
            callback_token: Token from webhook header.
            expected_token: Expected callback verification token.

        Returns:
            True if token matches.
        """
        import hmac
        return hmac.compare_digest(callback_token, expected_token)
