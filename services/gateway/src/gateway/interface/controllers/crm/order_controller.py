"""Order controller for CRM API endpoints.

This controller handles order management operations that were migrated
from the Commerce Agent service.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from commerce_agent.application.dto import (
    OrderDTO,
    AddOrderItemDTO,
    UpdateOrderStatusDTO,
    ConfirmOrderDTO,
    InitiatePaymentDTO,
)
from commerce_agent.application.services.order_service import OrderService
from gateway.crm.dependencies import get_order_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Orders"])


@router.get("/tenants/{tenant_id}/orders", response_model=list[OrderDTO])
async def list_orders(
    tenant_id: str,
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    order_service: OrderService = Depends(get_order_service),
) -> list[OrderDTO]:
    """List orders for a tenant."""
    return await order_service.list_orders(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status=status,
    )


@router.get("/orders/{order_id}", response_model=OrderDTO)
async def get_order(
    order_id: str,
    order_service: OrderService = Depends(get_order_service),
) -> OrderDTO:
    """Get order by ID."""
    order = await order_service.get_order(order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order not found: {order_id}",
        )

    return order


@router.post("/orders/{order_id}/items", response_model=OrderDTO)
async def add_order_item(
    order_id: str,
    dto: AddOrderItemDTO,
    order_service: OrderService = Depends(get_order_service),
) -> OrderDTO:
    """Add item to order."""
    try:
        return await order_service.add_item_to_order(order_id, dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/orders/{order_id}/items/{product_id}", response_model=OrderDTO)
async def remove_order_item(
    order_id: str,
    product_id: str,
    variant_sku: Optional[str] = Query(None),
    order_service: OrderService = Depends(get_order_service),
) -> OrderDTO:
    """Remove item from order."""
    try:
        return await order_service.remove_item_from_order(
            order_id, product_id, variant_sku
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/orders/{order_id}/confirm", response_model=OrderDTO)
async def confirm_order(
    order_id: str,
    dto: ConfirmOrderDTO | None = None,
    order_service: OrderService = Depends(get_order_service),
) -> OrderDTO:
    """Confirm order."""
    try:
        return await order_service.confirm_order(order_id, dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/orders/{order_id}/status", response_model=OrderDTO)
async def update_order_status(
    order_id: str,
    dto: UpdateOrderStatusDTO,
    order_service: OrderService = Depends(get_order_service),
) -> OrderDTO:
    """Update order status."""
    try:
        return await order_service.update_status(order_id, dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/orders/{order_id}/cancel", response_model=OrderDTO)
async def cancel_order(
    order_id: str,
    reason: Optional[str] = Query(None),
    order_service: OrderService = Depends(get_order_service),
) -> OrderDTO:
    """Cancel order."""
    try:
        return await order_service.cancel_order(order_id, reason)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/orders/{order_id}/payment")
async def initiate_payment(
    order_id: str,
    dto: InitiatePaymentDTO,
    order_service: OrderService = Depends(get_order_service),
) -> dict:
    """Initiate payment for order."""
    try:
        return await order_service.initiate_payment(order_id, dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
