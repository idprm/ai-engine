"""Order application service."""
import logging
from typing import Any

from crm_chatbot.application.dto import (
    OrderDTO,
    OrderItemDTO,
    CreateOrderDTO,
    AddOrderItemDTO,
    UpdateOrderStatusDTO,
    ConfirmOrderDTO,
    InitiatePaymentDTO,
)
from crm_chatbot.domain.entities import Order, OrderItem, Payment
from crm_chatbot.domain.repositories import OrderRepository, ProductRepository, PaymentRepository
from crm_chatbot.domain.value_objects import (
    OrderId,
    TenantId,
    CustomerId,
    ProductId,
    Money,
    OrderStatus,
    PaymentStatus,
)

logger = logging.getLogger(__name__)


class OrderService:
    """Application service for order operations."""

    def __init__(
        self,
        order_repository: OrderRepository,
        product_repository: ProductRepository,
        payment_repository: PaymentRepository,
        payment_client,  # MidtransClient or XenditClient
    ):
        self._order_repository = order_repository
        self._product_repository = product_repository
        self._payment_repository = payment_repository
        self._payment_client = payment_client

    async def get_order(self, order_id: str) -> OrderDTO | None:
        """Get an order by ID.

        Args:
            order_id: The order ID.

        Returns:
            OrderDTO if found, None otherwise.
        """
        order = await self._order_repository.get_by_id(
            OrderId.from_string(order_id)
        )

        if not order:
            return None

        return self._to_dto(order)

    async def create_order(self, tenant_id: str, dto: CreateOrderDTO) -> OrderDTO:
        """Create a new order.

        Args:
            tenant_id: The tenant ID.
            dto: Order creation data.

        Returns:
            Created OrderDTO.
        """
        order = Order.create(
            tenant_id=TenantId.from_string(tenant_id),
            customer_id=CustomerId.from_string(dto.customer_id),
            shipping_address=dto.shipping_address,
            notes=dto.notes,
        )

        # Add items if provided
        if dto.items:
            for item_dto in dto.items:
                item = OrderItem.create(
                    product_id=ProductId.from_string(item_dto.product_id),
                    product_name=item_dto.product_name,
                    variant_sku=item_dto.variant_sku,
                    quantity=item_dto.quantity,
                    unit_price=Money.from_float(item_dto.unit_price),
                )
                order.add_item(item)

        order = await self._order_repository.save(order)
        logger.info(f"Created order: {order.id}")

        return self._to_dto(order)

    async def get_or_create_active_order(
        self,
        tenant_id: str,
        customer_id: str,
    ) -> OrderDTO:
        """Get active order for customer or create new one.

        Args:
            tenant_id: The tenant ID.
            customer_id: The customer ID.

        Returns:
            OrderDTO for active/new order.
        """
        customer_id_vo = CustomerId.from_string(customer_id)

        # Try to get existing active order
        order = await self._order_repository.get_active_order_for_customer(customer_id_vo)

        if not order:
            # Create new order
            order = Order.create(
                tenant_id=TenantId.from_string(tenant_id),
                customer_id=customer_id_vo,
            )
            order = await self._order_repository.save(order)
            logger.info(f"Created new order for customer {customer_id}: {order.id}")

        return self._to_dto(order)

    async def add_item_to_order(
        self,
        order_id: str,
        dto: AddOrderItemDTO,
    ) -> OrderDTO:
        """Add an item to an order.

        Args:
            order_id: The order ID.
            dto: Item data.

        Returns:
            Updated OrderDTO.
        """
        order = await self._order_repository.get_by_id(
            OrderId.from_string(order_id)
        )

        if not order:
            raise ValueError(f"Order not found: {order_id}")

        # Get product for price and name
        product = await self._product_repository.get_by_id(
            ProductId.from_string(dto.product_id)
        )

        if not product:
            raise ValueError(f"Product not found: {dto.product_id}")

        # Determine price
        price = product.base_price
        variant_sku = dto.variant_sku

        if variant_sku:
            variant = product.get_variant(variant_sku)
            if not variant:
                raise ValueError(f"Variant not found: {variant_sku}")
            price = variant.price

        # Create and add item
        item = OrderItem.create(
            product_id=product.id,
            product_name=product.name,
            variant_sku=variant_sku,
            quantity=dto.quantity,
            unit_price=price,
        )

        order.add_item(item)
        order = await self._order_repository.save(order)

        return self._to_dto(order)

    async def remove_item_from_order(
        self,
        order_id: str,
        product_id: str,
        variant_sku: str | None = None,
    ) -> OrderDTO:
        """Remove an item from an order.

        Args:
            order_id: The order ID.
            product_id: The product ID.
            variant_sku: Optional variant SKU.

        Returns:
            Updated OrderDTO.
        """
        order = await self._order_repository.get_by_id(
            OrderId.from_string(order_id)
        )

        if not order:
            raise ValueError(f"Order not found: {order_id}")

        order.remove_item(
            ProductId.from_string(product_id),
            variant_sku,
        )
        order = await self._order_repository.save(order)

        return self._to_dto(order)

    async def confirm_order(
        self,
        order_id: str,
        dto: ConfirmOrderDTO | None = None,
    ) -> OrderDTO:
        """Confirm an order.

        Args:
            order_id: The order ID.
            dto: Optional confirmation data.

        Returns:
            Updated OrderDTO.
        """
        order = await self._order_repository.get_by_id(
            OrderId.from_string(order_id)
        )

        if not order:
            raise ValueError(f"Order not found: {order_id}")

        if dto and dto.shipping_address:
            order.set_shipping_address(dto.shipping_address)

        order.confirm()
        order = await self._order_repository.save(order)

        logger.info(f"Order confirmed: {order_id}")
        return self._to_dto(order)

    async def update_status(
        self,
        order_id: str,
        dto: UpdateOrderStatusDTO,
    ) -> OrderDTO:
        """Update order status.

        Args:
            order_id: The order ID.
            dto: Status update data.

        Returns:
            Updated OrderDTO.
        """
        order = await self._order_repository.get_by_id(
            OrderId.from_string(order_id)
        )

        if not order:
            raise ValueError(f"Order not found: {order_id}")

        new_status = OrderStatus(dto.status)

        # Handle status transitions
        if new_status == OrderStatus.PROCESSING:
            order.start_processing()
        elif new_status == OrderStatus.SHIPPED:
            order.ship()
        elif new_status == OrderStatus.DELIVERED:
            order.deliver()
        elif new_status == OrderStatus.CANCELLED:
            order.cancel(dto.notes)
        else:
            raise ValueError(f"Invalid status transition to: {dto.status}")

        order = await self._order_repository.save(order)
        return self._to_dto(order)

    async def cancel_order(
        self,
        order_id: str,
        reason: str | None = None,
    ) -> OrderDTO:
        """Cancel an order.

        Args:
            order_id: The order ID.
            reason: Cancellation reason.

        Returns:
            Updated OrderDTO.
        """
        order = await self._order_repository.get_by_id(
            OrderId.from_string(order_id)
        )

        if not order:
            raise ValueError(f"Order not found: {order_id}")

        order.cancel(reason)
        order = await self._order_repository.save(order)

        logger.info(f"Order cancelled: {order_id}")
        return self._to_dto(order)

    async def initiate_payment(
        self,
        order_id: str,
        dto: InitiatePaymentDTO,
    ) -> dict[str, Any]:
        """Initiate payment for an order.

        Args:
            order_id: The order ID.
            dto: Payment initiation data.

        Returns:
            Payment details including URL/QR code.
        """
        order = await self._order_repository.get_by_id(
            OrderId.from_string(order_id)
        )

        if not order:
            raise ValueError(f"Order not found: {order_id}")

        # Check if payment already exists
        existing_payment = await self._payment_repository.get_by_order_id(order.id)
        if existing_payment and existing_payment.is_pending:
            return {
                "payment_id": existing_payment.id,
                "order_id": str(order.id),
                "status": existing_payment.status.value,
                "payment_url": existing_payment.payment_url,
                "qr_code": existing_payment.qr_code,
                "expired_at": existing_payment.expired_at.isoformat() if existing_payment.expired_at else None,
            }

        # Create payment with gateway
        payment_result = await self._payment_client.create_transaction(
            order_id=str(order.id),
            amount=order.total.to_float(),
            payment_type=dto.payment_method,
        )

        # Create payment entity
        from datetime import datetime
        payment = Payment.create(
            payment_id=payment_result["transaction_id"],
            order_id=order.id,
            amount=order.total,
            payment_url=payment_result.get("payment_url"),
            expired_at=datetime.fromisoformat(payment_result["expiry_time"]) if payment_result.get("expiry_time") else None,
        )

        payment.set_payment_details(
            payment_method=dto.payment_method,
            payment_type=payment_result.get("payment_type"),
            payment_url=payment_result.get("payment_url"),
            qr_code=payment_result.get("qr_string") or payment_result.get("va_number"),
        )

        payment.mark_pending_payment()
        await self._payment_repository.save(payment)

        # Update order with payment ID
        order.set_payment_id(payment.id)
        await self._order_repository.save(order)

        logger.info(f"Payment initiated for order {order_id}: {payment.id}")

        return {
            "payment_id": payment.id,
            "order_id": str(order.id),
            "amount": payment.amount.to_float(),
            "status": payment.status.value,
            "payment_method": payment.payment_method,
            "payment_url": payment.payment_url,
            "qr_code": payment.qr_code,
            "expired_at": payment.expired_at.isoformat() if payment.expired_at else None,
        }

    async def list_orders(
        self,
        tenant_id: str,
        customer_id: str | None = None,
        status: str | None = None,
    ) -> list[OrderDTO]:
        """List orders.

        Args:
            tenant_id: The tenant ID.
            customer_id: Optional customer filter.
            status: Optional status filter.

        Returns:
            List of OrderDTOs.
        """
        if customer_id:
            status_filter = OrderStatus(status) if status else None
            orders = await self._order_repository.list_by_customer(
                CustomerId.from_string(customer_id),
                status=status_filter,
            )
        else:
            status_filter = OrderStatus(status) if status else None
            orders = await self._order_repository.list_by_tenant(
                TenantId.from_string(tenant_id),
                status=status_filter,
            )

        return [self._to_dto(o) for o in orders]

    def _to_dto(self, order: Order) -> OrderDTO:
        """Convert entity to DTO."""
        return OrderDTO(
            id=str(order.id),
            tenant_id=str(order.tenant_id),
            customer_id=str(order.customer_id),
            items=[
                OrderItemDTO(
                    product_id=str(item.product_id),
                    product_name=item.product_name,
                    variant_sku=item.variant_sku,
                    quantity=item.quantity,
                    unit_price=item.unit_price.to_float(),
                    subtotal=item.subtotal.to_float(),
                )
                for item in order.items
            ],
            status=order.status.value,
            payment_status=order.payment_status.value,
            subtotal=order.subtotal.to_float(),
            shipping_cost=order.shipping_cost.to_float(),
            total=order.total.to_float(),
            currency="IDR",
            shipping_address=order.shipping_address,
            payment_id=order.payment_id,
            notes=order.notes,
            item_count=order.item_count,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
