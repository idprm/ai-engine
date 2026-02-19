"""Agent state definitions for multi-agent LangGraph workflows."""
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the multi-agent LangGraph workflow.

    Attributes:
        messages: Conversation messages with automatic message aggregation.
        agent_type: The type of agent that should process this request.
        context: Additional context for agent routing and processing.
        needs_moderation: Whether the content requires moderation check.
        moderation_result: Result of moderation if performed.
        retry_count: Number of retry attempts for failed processing.
        final_response: The final response to return to the user.
        error: Error message if processing failed.
    """
    messages: Annotated[list, add_messages]
    agent_type: Literal["main", "fallback", "followup", "moderation"]
    context: dict[str, Any]
    needs_moderation: bool
    moderation_result: dict[str, Any] | None
    retry_count: int
    final_response: str | None
    error: str | None


def create_initial_state(
    user_message: str,
    agent_type: str = "main",
    context: dict[str, Any] | None = None,
    needs_moderation: bool = True,
) -> AgentState:
    """Create an initial agent state with default values.

    Args:
        user_message: The user's input message.
        agent_type: The initial agent type to route to.
        context: Optional context dictionary.
        needs_moderation: Whether to perform moderation check.

    Returns:
        Initialized AgentState dictionary.
    """
    from langchain_core.messages import HumanMessage

    return AgentState(
        messages=[HumanMessage(content=user_message)],
        agent_type=agent_type,
        context=context or {},
        needs_moderation=needs_moderation,
        moderation_result=None,
        retry_count=0,
        final_response=None,
        error=None,
    )
