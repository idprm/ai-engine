"""Tool registry for CRM agent tools."""
import logging
from typing import Any, Callable

from langchain_core.tools import BaseTool, StructuredTool

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
from crm_chatbot.infrastructure.llm.tools.label_tools import (
    label_conversation,
    get_available_labels,
    remove_label,
)

logger = logging.getLogger(__name__)


# Tool categories
PRODUCT_TOOLS = ["search_products", "get_product_details", "check_stock"]
ORDER_TOOLS = [
    "create_order",
    "add_to_order",
    "get_order_status",
    "get_customer_orders",
    "confirm_order",
    "cancel_order",
]
CUSTOMER_TOOLS = ["get_customer_profile", "update_customer_profile"]
PAYMENT_TOOLS = ["initiate_payment", "check_payment_status"]
LABEL_TOOLS = ["label_conversation", "get_available_labels", "remove_label"]


def get_all_tools() -> list[BaseTool]:
    """Get all available CRM tools.

    Returns:
        List of all LangChain tools.
    """
    return [
        # Product tools
        search_products,
        get_product_details,
        check_stock,
        # Order tools
        create_order,
        add_to_order,
        get_order_status,
        get_customer_orders,
        confirm_order,
        cancel_order,
        # Customer tools
        get_customer_profile,
        update_customer_profile,
        # Payment tools
        initiate_payment,
        check_payment_status,
        # Label tools
        label_conversation,
        get_available_labels,
        remove_label,
    ]


def get_tools_by_category(category: str) -> list[BaseTool]:
    """Get tools by category.

    Args:
        category: Category name (product, order, customer, payment, label).

    Returns:
        List of tools in the category.
    """
    all_tools = get_all_tools()
    tool_map = {tool.name: tool for tool in all_tools}

    categories = {
        "product": PRODUCT_TOOLS,
        "order": ORDER_TOOLS,
        "customer": CUSTOMER_TOOLS,
        "payment": PAYMENT_TOOLS,
        "label": LABEL_TOOLS,
    }

    if category not in categories:
        logger.warning(f"Unknown tool category: {category}")
        return []

    return [tool_map[name] for name in categories[category] if name in tool_map]


def get_tools_for_conversation_state(state: str) -> list[BaseTool]:
    """Get appropriate tools for a conversation state.

    Args:
        state: Current conversation state.

    Returns:
        List of tools appropriate for the state.
    """
    state_tool_map = {
        "greeting": ["get_customer_profile"],
        "browsing": ["search_products", "get_product_details", "check_stock", "create_order"],
        "ordering": [
            "add_to_order",
            "get_order_status",
            "get_customer_orders",
            "create_order",
            "cancel_order",
        ],
        "checkout": ["confirm_order", "get_order_status", "cancel_order"],
        "payment": ["initiate_payment", "check_payment_status"],
        "support": ["get_customer_profile", "get_order_status", "get_customer_orders", "label_conversation", "get_available_labels"],
    }

    all_tools = get_all_tools()
    tool_map = {tool.name: tool for tool in all_tools}

    tool_names = state_tool_map.get(state, [])
    return [tool_map[name] for name in tool_names if name in tool_map]


# Tool executor registry
# Maps tool names to their executor functions
TOOL_EXECUTORS: dict[str, Callable] = {
    # Product tools
    "search_products": None,  # Will be set by service layer
    "get_product_details": None,
    "check_stock": None,
    # Order tools
    "create_order": None,
    "add_to_order": None,
    "get_order_status": None,
    "get_customer_orders": None,
    "confirm_order": None,
    "cancel_order": None,
    # Customer tools
    "get_customer_profile": None,
    "update_customer_profile": None,
    # Payment tools
    "initiate_payment": None,
    "check_payment_status": None,
    # Label tools
    "label_conversation": None,
    "get_available_labels": None,
    "remove_label": None,
}


def register_tool_executor(tool_name: str, executor: Callable) -> None:
    """Register an executor function for a tool.

    Args:
        tool_name: Name of the tool.
        executor: Async function to execute the tool.
    """
    TOOL_EXECUTORS[tool_name] = executor
    logger.debug(f"Registered executor for tool: {tool_name}")


def get_tool_executor(tool_name: str) -> Callable | None:
    """Get the executor for a tool.

    Args:
        tool_name: Name of the tool.

    Returns:
        Executor function or None if not registered.
    """
    return TOOL_EXECUTORS.get(tool_name)
