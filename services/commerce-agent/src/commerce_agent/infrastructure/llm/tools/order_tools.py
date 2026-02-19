"""Order tools for CRM agent."""
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def create_order() -> str:
    """Create a new empty order for the customer.

    Use this tool when the customer wants to start placing an order.
    Returns the new order ID.

    Returns:
        JSON string with order ID.
    """
    import json
    return json.dumps({
        "order_id": None,
        "message": "Create order requires customer context - will be executed by service",
    })


@tool
async def add_to_order(
    product_id: str,
    quantity: int,
    variant_sku: str | None = None,
) -> str:
    """Add a product to the current order.

    Use this tool when the customer wants to add items to their order.
    If no active order exists, one will be created.

    Args:
        product_id: The ID of the product to add.
        quantity: The quantity to add.
        variant_sku: Optional SKU of the specific variant.

    Returns:
        JSON string with updated order summary.
    """
    import json
    return json.dumps({
        "order": None,
        "message": "Add to order requires order context - will be executed by service",
    })


@tool
async def get_order_status(order_id: str) -> str:
    """Get the status of a specific order.

    Use this tool when the customer wants to check their order status.

    Args:
        order_id: The unique identifier of the order.

    Returns:
        JSON string with order status and details.
    """
    import json
    return json.dumps({
        "order": None,
        "message": "Get order requires context - will be executed by service",
    })


@tool
async def get_customer_orders(status: str | None = None) -> str:
    """Get the order history for the current customer.

    Use this tool when the customer wants to see their order history.

    Args:
        status: Optional status filter (PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED).

    Returns:
        JSON string with list of orders.
    """
    import json
    return json.dumps({
        "orders": [],
        "message": "Get customer orders requires customer context - will be executed by service",
    })


@tool
async def confirm_order(order_id: str, shipping_address: dict | None = None) -> str:
    """Confirm an order to proceed to payment.

    Use this tool when the customer confirms their order and is ready to pay.
    Optionally updates the shipping address.

    Args:
        order_id: The ID of the order to confirm.
        shipping_address: Optional shipping address dict with fields:
            - street: Street address
            - city: City name
            - province: Province/state
            - postal_code: Postal/zip code
            - country: Country code

    Returns:
        JSON string with confirmed order details.
    """
    import json
    return json.dumps({
        "order": None,
        "message": "Confirm order requires context - will be executed by service",
    })


@tool
async def cancel_order(order_id: str, reason: str | None = None) -> str:
    """Cancel an order.

    Use this tool when the customer wants to cancel their order.
    Only pending or confirmed orders can be cancelled.

    Args:
        order_id: The ID of the order to cancel.
        reason: Optional reason for cancellation.

    Returns:
        JSON string with cancellation confirmation.
    """
    import json
    return json.dumps({
        "order": None,
        "message": "Cancel order requires context - will be executed by service",
    })


# Tool executor functions
async def execute_create_order(
    order_repository,
    tenant_id: str,
    customer_id: str,
) -> dict[str, Any]:
    """Execute order creation with repository access."""
    from commerce_agent.domain.entities import Order
    from commerce_agent.domain.value_objects import TenantId, CustomerId

    order = Order.create(
        tenant_id=TenantId.from_string(tenant_id),
        customer_id=CustomerId.from_string(customer_id),
    )

    saved_order = await order_repository.save(order)

    return {
        "order_id": str(saved_order.id),
        "status": saved_order.status.value,
        "total": saved_order.total.to_float(),
        "item_count": saved_order.item_count,
    }


async def execute_add_to_order(
    order_repository,
    product_repository,
    tenant_id: str,
    customer_id: str,
    product_id: str,
    quantity: int,
    variant_sku: str | None = None,
) -> dict[str, Any]:
    """Execute add to order with repository access."""
    from commerce_agent.domain.entities import OrderItem
    from commerce_agent.domain.value_objects import TenantId, CustomerId, ProductId

    # Get or create active order
    order = await order_repository.get_active_order_for_customer(
        CustomerId.from_string(customer_id)
    )

    if not order:
        order = await execute_create_order(
            order_repository, tenant_id, customer_id
        )
        order = await order_repository.get_by_id(
            order["order_id"]
        )

    # Get product details
    product = await product_repository.get_by_id(
        ProductId.from_string(product_id)
    )

    if not product:
        return {"error": "Product not found"}

    # Determine price
    price = product.base_price
    variant_name = None

    if variant_sku:
        variant = product.get_variant(variant_sku)
        if not variant:
            return {"error": f"Variant {variant_sku} not found"}
        price = variant.price
        variant_name = variant.name

    # Create and add item
    item = OrderItem.create(
        product_id=ProductId.from_string(product_id),
        product_name=product.name,
        variant_sku=variant_sku,
        quantity=quantity,
        unit_price=price,
    )

    order.add_item(item)
    await order_repository.save(order)

    return {
        "order_id": str(order.id),
        "status": order.status.value,
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "subtotal": item.subtotal.to_float(),
            }
            for item in order.items
        ],
        "subtotal": order.subtotal.to_float(),
        "total": order.total.to_float(),
    }


async def execute_get_order_status(
    order_repository,
    order_id: str,
) -> dict[str, Any]:
    """Execute get order status with repository access."""
    from commerce_agent.domain.value_objects import OrderId

    order = await order_repository.get_by_id(
        OrderId.from_string(order_id)
    )

    if not order:
        return {"error": "Order not found", "order_id": order_id}

    return {
        "order_id": str(order.id),
        "status": order.status.value,
        "payment_status": order.payment_status.value,
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "subtotal": item.subtotal.to_float(),
            }
            for item in order.items
        ],
        "subtotal": order.subtotal.to_float(),
        "shipping_cost": order.shipping_cost.to_float(),
        "total": order.total.to_float(),
        "created_at": order.created_at.isoformat(),
    }


async def execute_get_customer_orders(
    order_repository,
    customer_id: str,
    status: str | None = None,
) -> dict[str, Any]:
    """Execute get customer orders with repository access."""
    from commerce_agent.domain.value_objects import CustomerId, OrderStatus

    status_filter = OrderStatus(status) if status else None

    orders = await order_repository.list_by_customer(
        CustomerId.from_string(customer_id),
        status=status_filter,
    )

    return {
        "orders": [
            {
                "order_id": str(order.id),
                "status": order.status.value,
                "total": order.total.to_float(),
                "item_count": order.item_count,
                "created_at": order.created_at.isoformat(),
            }
            for order in orders
        ],
        "total": len(orders),
    }


async def execute_confirm_order(
    order_repository,
    order_id: str,
    shipping_address: dict | None = None,
) -> dict[str, Any]:
    """Execute order confirmation with repository access."""
    from commerce_agent.domain.value_objects import OrderId

    order = await order_repository.get_by_id(
        OrderId.from_string(order_id)
    )

    if not order:
        return {"error": "Order not found", "order_id": order_id}

    if shipping_address:
        order.set_shipping_address(shipping_address)

    order.confirm()
    await order_repository.save(order)

    return {
        "order_id": str(order.id),
        "status": order.status.value,
        "payment_status": order.payment_status.value,
        "total": order.total.to_float(),
        "shipping_address": order.shipping_address,
        "message": "Order confirmed, ready for payment",
    }


async def execute_cancel_order(
    order_repository,
    order_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Execute order cancellation with repository access."""
    from commerce_agent.domain.value_objects import OrderId

    order = await order_repository.get_by_id(
        OrderId.from_string(order_id)
    )

    if not order:
        return {"error": "Order not found", "order_id": order_id}

    order.cancel(reason)
    await order_repository.save(order)

    return {
        "order_id": str(order.id),
        "status": order.status.value,
        "message": "Order cancelled successfully",
    }
