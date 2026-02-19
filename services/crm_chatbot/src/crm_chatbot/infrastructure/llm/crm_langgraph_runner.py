"""CRM LangGraph runner for executing chatbot AI pipelines."""
import json
import logging
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from crm_chatbot.infrastructure.llm.crm_agent_state import CRMAgentState, create_crm_initial_state
from crm_chatbot.infrastructure.llm.tools import get_tools_for_conversation_state, get_tool_executor
from ai_engine.infrastructure.llm.llm_factory import LLMFactory
from ai_engine.domain.entities import LLMConfig

logger = logging.getLogger(__name__)


class CRMLangGraphRunner:
    """Runner for executing CRM chatbot AI pipelines with LangGraph.

    Creates and executes a tool-calling agent that:
    1. Analyzes the user's message and conversation context
    2. Selects appropriate tools based on intent
    3. Executes tools to fetch/modify data
    4. Generates a helpful response
    """

    def __init__(self):
        self._graphs: dict[str, StateGraph] = {}

    async def run(
        self,
        config: LLMConfig,
        system_prompt: str,
        tenant_id: str,
        customer_id: str,
        conversation_id: str,
        user_message: str,
        customer_context: dict[str, Any] | None = None,
        conversation_state: str = "greeting",
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, int, dict[str, Any]]:
        """Run the CRM chatbot agent pipeline.

        Args:
            config: LLM configuration entity.
            system_prompt: System prompt for the agent.
            tenant_id: The tenant ID.
            customer_id: The customer ID.
            conversation_id: The conversation ID.
            user_message: The user's message.
            customer_context: Optional customer context.
            conversation_state: Current conversation state.
            conversation_history: Optional previous messages.

        Returns:
            Tuple of (response text, tokens used, metadata dict).
        """
        logger.info(f"Starting CRM agent for conversation: {conversation_id}")

        # Get tools for current conversation state
        tools = get_tools_for_conversation_state(conversation_state)

        # Build the workflow
        workflow = self._build_workflow(config, tools, system_prompt)

        # Compile the graph
        graph = workflow.compile()

        # Create initial state
        initial_state = create_crm_initial_state(
            tenant_id=tenant_id,
            customer_id=customer_id,
            conversation_id=conversation_id,
            user_message=user_message,
            customer_context=customer_context,
            conversation_state=conversation_state,
        )

        # Add conversation history
        if conversation_history:
            history_messages = []
            for msg in conversation_history:
                if msg["role"] == "user":
                    history_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    history_messages.append(AIMessage(content=msg["content"]))

            initial_state["messages"] = history_messages + initial_state["messages"]

        # Execute
        result = await graph.ainvoke(initial_state)

        # Extract response
        final_response = result.get("final_response")
        if not final_response and result.get("messages"):
            # Get the last AI message
            for msg in reversed(result["messages"]):
                if isinstance(msg, AIMessage):
                    final_response = msg.content
                    break

        # Extract tokens
        tokens_used = 0
        if result.get("messages"):
            last_message = result["messages"][-1]
            tokens_used = self._extract_tokens(last_message)

        # Build metadata
        metadata = {
            "intent": result.get("intent", "general"),
            "conversation_state": result.get("conversation_state"),
            "tools_used": list(result.get("tool_results", {}).keys()),
            "needs_clarification": result.get("needs_clarification", False),
        }

        logger.info(f"CRM agent complete for {conversation_id}, tokens: {tokens_used}")

        return final_response or "", tokens_used, metadata

    def _build_workflow(
        self,
        config: LLMConfig,
        tools: list[BaseTool],
        system_prompt: str,
    ) -> StateGraph:
        """Build the CRM agent workflow graph.

        Args:
            config: LLM configuration.
            tools: Available tools.
            system_prompt: System prompt for the agent.

        Returns:
            StateGraph for the workflow.
        """
        # Create LLM with tool binding
        llm = LLMFactory.create(config)

        if tools:
            llm = llm.bind_tools(tools)

        async def agent_node(state: CRMAgentState) -> dict:
            """Agent node that processes the message and decides actions."""
            messages = state["messages"]

            # Build context
            context_info = self._build_context_info(state)
            full_system_prompt = f"{system_prompt}\n\n{context_info}"

            # Call LLM
            full_messages = [SystemMessage(content=full_system_prompt)] + list(messages)
            response = await llm.ainvoke(full_messages)

            return {"messages": [response]}

        async def tool_executor_node(state: CRMAgentState) -> dict:
            """Execute tools requested by the agent."""
            tool_results = {}
            new_messages = []

            last_message = state["messages"][-1]

            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return {"tool_results": tool_results}

            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                logger.debug(f"Executing tool: {tool_name} with args: {tool_args}")

                try:
                    # Get the tool executor
                    executor = get_tool_executor(tool_name)

                    if executor:
                        # Inject context into args
                        tool_args["tenant_id"] = state["tenant_id"]
                        tool_args["customer_id"] = state["customer_id"]

                        # Execute
                        result = await executor(**tool_args)
                        tool_results[tool_name] = result

                        # Add tool message
                        new_messages.append(
                            ToolMessage(
                                content=json.dumps(result),
                                tool_call_id=tool_call["id"],
                            )
                        )
                    else:
                        # Tool not registered
                        error_result = {"error": f"Tool {tool_name} not available"}
                        tool_results[tool_name] = error_result
                        new_messages.append(
                            ToolMessage(
                                content=json.dumps(error_result),
                                tool_call_id=tool_call["id"],
                            )
                        )

                except Exception as e:
                    logger.error(f"Tool execution failed: {tool_name}: {e}")
                    error_result = {"error": str(e)}
                    tool_results[tool_name] = error_result
                    new_messages.append(
                        ToolMessage(
                            content=json.dumps(error_result),
                            tool_call_id=tool_call["id"],
                        )
                    )

            return {
                "messages": new_messages,
                "tool_results": tool_results,
            }

        def should_continue(state: CRMAgentState) -> str:
            """Determine if we should continue tool execution or end."""
            last_message = state["messages"][-1]

            # If the last message has tool calls, execute tools
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"

            # Otherwise, we're done
            return "end"

        async def finalize_node(state: CRMAgentState) -> dict:
            """Finalize the response."""
            last_message = state["messages"][-1]

            final_response = None
            if isinstance(last_message, AIMessage):
                final_response = last_message.content

            return {"final_response": final_response}

        # Build the graph
        workflow = StateGraph(CRMAgentState)

        # Add nodes
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_executor_node)
        workflow.add_node("finalize", finalize_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                "end": "finalize",
            },
        )

        # Tools return to agent for processing
        workflow.add_edge("tools", "agent")

        # Finalize ends
        workflow.add_edge("finalize", END)

        return workflow

    def _build_context_info(self, state: CRMAgentState) -> str:
        """Build context information string for the agent.

        Args:
            state: Current agent state.

        Returns:
            Context information string.
        """
        context_parts = []

        # Conversation context
        context_parts.append(f"Conversation ID: {state['conversation_id']}")
        context_parts.append(f"Current State: {state['conversation_state']}")

        # Customer context
        customer_ctx = state.get("customer_context", {})
        if customer_ctx:
            if customer_ctx.get("name"):
                context_parts.append(f"Customer Name: {customer_ctx['name']}")
            if customer_ctx.get("total_orders"):
                context_parts.append(f"Total Orders: {customer_ctx['total_orders']}")
            if customer_ctx.get("is_vip"):
                context_parts.append("Customer is VIP")

        # Available tools
        tools = get_tools_for_conversation_state(state["conversation_state"])
        if tools:
            tool_names = [t.name for t in tools]
            context_parts.append(f"Available Tools: {', '.join(tool_names)}")

        return "\n".join(context_parts)

    def _extract_tokens(self, message: BaseMessage) -> int:
        """Extract token usage from a message.

        Args:
            message: The message to extract tokens from.

        Returns:
            Number of tokens used, or 0 if not available.
        """
        if hasattr(message, "response_metadata"):
            metadata = message.response_metadata
            if "token_usage" in metadata:
                return metadata["token_usage"].get("total_tokens", 0)
        return 0
