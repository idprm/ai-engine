"""CRM LangGraph tools for agent use."""

from crm_chatbot.infrastructure.llm.tools.product_tools import (
    search_products,
    get_product_details,
    check_stock,
)
from crm_chatbot.infrastructure.llm.tools.order_tools import (
    create_order,
    add_to_order,
    get_order_status,
    get_customer_orders,
    confirm_order,
    cancel_order,
)
from crm_chatbot.infrastructure.llm.tools.customer_tools import (
    get_customer_profile,
    update_customer_profile,
)
from crm_chatbot.infrastructure.llm.tools.payment_tools import (
    initiate_payment,
    check_payment_status,
)
from crm_chatbot.infrastructure.llm.tools.tool_registry import (
    get_all_tools,
    get_tools_by_category,
)

__all__ = [
    # Product tools
    "search_products",
    "get_product_details",
    "check_stock",
    # Order tools
    "create_order",
    "add_to_order",
    "get_order_status",
    "get_customer_orders",
    "confirm_order",
    "cancel_order",
    # Customer tools
    "get_customer_profile",
    "update_customer_profile",
    # Payment tools
    "initiate_payment",
    "check_payment_status",
    # Registry
    "get_all_tools",
    "get_tools_by_category",
]
