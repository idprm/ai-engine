"""CRM Agent state definitions for LangGraph workflows."""
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


class CRMAgentState(TypedDict):
    """State for the CRM agent LangGraph workflow.

    Attributes:
        messages: Conversation messages with automatic message aggregation.
        tenant_id: The tenant (business) ID.
        customer_id: The customer ID.
        conversation_id: The conversation ID.
        customer_context: Customer profile and history context.
        conversation_state: Current state of the conversation (greeting, browsing, etc.).
        intent: Detected intent from the user message.
        available_tools: List of tools available for the current context.
        tool_results: Results from tool executions.
        final_response: The final response to send to the customer.
        needs_clarification: Whether the agent needs more information.
        clarification_question: Question to ask for clarification.
        error: Error message if processing failed.
    """
    messages: Annotated[list, add_messages]
    tenant_id: str
    customer_id: str
    conversation_id: str
    customer_context: dict[str, Any]
    conversation_state: str  # greeting, browsing, ordering, checkout, payment, support
    intent: str  # product_inquiry, order_status, place_order, general, etc.
    available_tools: list[str]
    tool_results: dict[str, Any]
    final_response: str | None
    needs_clarification: bool
    clarification_question: str | None
    error: str | None


def create_crm_initial_state(
    tenant_id: str,
    customer_id: str,
    conversation_id: str,
    user_message: str,
    customer_context: dict[str, Any] | None = None,
    conversation_state: str = "greeting",
) -> CRMAgentState:
    """Create an initial CRM agent state.

    Args:
        tenant_id: The tenant ID.
        customer_id: The customer ID.
        conversation_id: The conversation ID.
        user_message: The user's message.
        customer_context: Optional customer context.
        conversation_state: Initial conversation state.

    Returns:
        Initialized CRMAgentState dictionary.
    """
    from langchain_core.messages import HumanMessage

    return CRMAgentState(
        messages=[HumanMessage(content=user_message)],
        tenant_id=tenant_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        customer_context=customer_context or {},
        conversation_state=conversation_state,
        intent="general",
        available_tools=[],
        tool_results={},
        final_response=None,
        needs_clarification=False,
        clarification_question=None,
        error=None,
    )
