"""CRM LangGraph tools for agent use."""

from commerce_agent.infrastructure.llm.tools.product_tools import (
    search_products,
    get_product_details,
    check_stock,
)
from commerce_agent.infrastructure.llm.tools.order_tools import (
    create_order,
    add_to_order,
    get_order_status,
    get_customer_orders,
    confirm_order,
    cancel_order,
)
from commerce_agent.infrastructure.llm.tools.customer_tools import (
    get_customer_profile,
    update_customer_profile,
)
from commerce_agent.infrastructure.llm.tools.payment_tools import (
    initiate_payment,
    check_payment_status,
)
from commerce_agent.infrastructure.llm.tools.tool_registry import (
    get_all_tools,
    get_tools_by_category,
    get_tools_for_conversation_state,
    get_tool_executor,
    register_tool_executor,
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
    "get_tools_for_conversation_state",
    "get_tool_executor",
    "register_tool_executor",
]
