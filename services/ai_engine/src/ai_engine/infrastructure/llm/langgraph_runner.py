"""LangGraph runner for executing AI pipelines."""
import logging
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from ai_engine.domain.entities import LLMConfig
from ai_engine.infrastructure.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the LangGraph agent."""
    messages: Annotated[list[BaseMessage], add_messages]


class LangGraphRunner:
    """Runner for executing LangGraph-based AI pipelines.

    Creates and executes a simple single-node graph that:
    1. Combines system prompt with user message
    2. Invokes the LLM
    3. Returns the response
    """

    def __init__(self):
        self._graphs: dict[str, StateGraph] = {}

    async def run(
        self,
        config: LLMConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, int]:
        """Run the LangGraph pipeline.

        Args:
            config: LLM configuration entity.
            system_prompt: System prompt text.
            user_prompt: User prompt text.

        Returns:
            Tuple of (response text, tokens used).
        """
        # Create LLM instance
        llm = LLMFactory.create(config)

        # Create the agent node function
        async def agent_node(state: AgentState) -> dict:
            """Agent node that calls the LLM."""
            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await llm.ainvoke(messages)
            return {"messages": [response]}

        # Build the graph
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)

        graph = workflow.compile()

        # Execute the graph
        inputs: AgentState = {
            "messages": [HumanMessage(content=user_prompt)]
        }
        result = await graph.ainvoke(inputs)

        # Extract response
        response_message = result["messages"][-1]
        response_text = response_message.content

        # Get token usage if available
        tokens_used = 0
        if hasattr(response_message, "response_metadata"):
            metadata = response_message.response_metadata
            if "token_usage" in metadata:
                tokens_used = metadata["token_usage"].get("total_tokens", 0)

        logger.debug(f"LangGraph execution complete, tokens: {tokens_used}")

        return response_text, tokens_used

    async def run_with_history(
        self,
        config: LLMConfig,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> tuple[str, int]:
        """Run the LangGraph pipeline with conversation history.

        Args:
            config: LLM configuration entity.
            system_prompt: System prompt text.
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            Tuple of (response text, tokens used).
        """
        llm = LLMFactory.create(config)

        async def agent_node(state: AgentState) -> dict:
            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await llm.ainvoke(messages)
            return {"messages": [response]}

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)

        graph = workflow.compile()

        # Convert message dicts to LangChain messages
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            # Add other role types as needed

        inputs: AgentState = {"messages": langchain_messages}
        result = await graph.ainvoke(inputs)

        response_message = result["messages"][-1]
        response_text = response_message.content

        tokens_used = 0
        if hasattr(response_message, "response_metadata"):
            metadata = response_message.response_metadata
            if "token_usage" in metadata:
                tokens_used = metadata["token_usage"].get("total_tokens", 0)

        return response_text, tokens_used
