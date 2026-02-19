"""Customer tools for CRM agent."""
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def get_customer_profile() -> str:
    """Get the profile of the current customer.

    Use this tool to retrieve customer information like name,
    address, order history summary, and tags.

    Returns:
        JSON string with customer profile.
    """
    import json
    return json.dumps({
        "customer": None,
        "message": "Get customer requires customer context - will be executed by service",
    })


@tool
async def update_customer_profile(
    name: str | None = None,
    email: str | None = None,
    address: dict | None = None,
) -> str:
    """Update the customer's profile information.

    Use this tool when the customer wants to update their information.

    Args:
        name: New name for the customer.
        email: New email address.
        address: New address dict with fields:
            - street: Street address
            - city: City name
            - province: Province/state
            - postal_code: Postal/zip code
            - country: Country code

    Returns:
        JSON string with updated profile.
    """
    import json
    return json.dumps({
        "customer": None,
        "message": "Update customer requires customer context - will be executed by service",
    })


# Tool executor functions
async def execute_get_customer_profile(
    customer_repository,
    customer_id: str,
) -> dict[str, Any]:
    """Execute get customer profile with repository access."""
    from crm_chatbot.domain.value_objects import CustomerId

    customer = await customer_repository.get_by_id(
        CustomerId.from_string(customer_id)
    )

    if not customer:
        return {"error": "Customer not found"}

    return {
        "customer_id": str(customer.id),
        "phone_number": str(customer.phone_number),
        "name": customer.name,
        "email": customer.email,
        "address": customer.address,
        "tags": customer.tags,
        "total_orders": customer.total_orders,
        "total_spent": customer.total_spent.to_float(),
        "is_vip": customer.is_vip(),
    }


async def execute_update_customer_profile(
    customer_repository,
    customer_id: str,
    name: str | None = None,
    email: str | None = None,
    address: dict | None = None,
) -> dict[str, Any]:
    """Execute update customer profile with repository access."""
    from crm_chatbot.domain.value_objects import CustomerId

    customer = await customer_repository.get_by_id(
        CustomerId.from_string(customer_id)
    )

    if not customer:
        return {"error": "Customer not found"}

    customer.update_profile(name=name, email=email, address=address)
    await customer_repository.save(customer)

    return {
        "customer_id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "address": customer.address,
        "message": "Profile updated successfully",
    }
