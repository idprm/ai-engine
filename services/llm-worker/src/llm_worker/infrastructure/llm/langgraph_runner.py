"""LangGraph runner for executing multi-agent AI pipelines."""
import logging
from typing import Any, Literal

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from llm_worker.domain.entities import AgentConfig, AgentType, LLMConfig
from llm_worker.infrastructure.llm.agent_nodes import (
    fallback_agent_node,
    followup_agent_node,
    main_agent_node,
    moderation_node,
    router_node,
)
from llm_worker.infrastructure.llm.agent_state import AgentState, create_initial_state
from llm_worker.infrastructure.llm.backoff import (
    BackoffConfig,
    BackoffExhaustedError,
    retry_with_backoff,
)
from llm_worker.infrastructure.llm.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitOpenError,
)
from llm_worker.infrastructure.llm.llm_factory import LLMFactory
from llm_worker.infrastructure.llm.timeout import LLMTimeoutError, with_timeout

logger = logging.getLogger(__name__)

# Default backoff configuration for graph execution retries
DEFAULT_BACKOFF_CONFIG = BackoffConfig(
    initial_delay=1.0,
    max_delay=30.0,
    multiplier=2.0,
)

# Retryable exceptions that should trigger a retry at the graph level
RETRYABLE_EXCEPTIONS = (LLMTimeoutError, ConnectionError, ConnectionResetError)


class LangGraphRunner:
    """Runner for executing LangGraph-based multi-agent AI pipelines.

    Creates and executes a multi-agent graph that:
    1. Moderates content for policy violations
    2. Routes to appropriate agent based on message type
    3. Processes with main, followup, or fallback agents
    4. Handles errors with fallback mechanisms
    """

    def __init__(self):
        self._graphs: dict[str, StateGraph] = {}

    async def run(
        self,
        config: LLMConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, int]:
        """Run the simple single-agent LangGraph pipeline (backward compatible).

        Args:
            config: LLM configuration entity.
            system_prompt: System prompt text.
            user_prompt: User prompt text.

        Returns:
            Tuple of (response text, tokens used).
        """
        from llm_worker.infrastructure.llm.agent_state import AgentState as SimpleState

        # Create LLM instance
        llm = LLMFactory.create(config)

        # Get circuit breaker for this LLM config
        registry = CircuitBreakerRegistry.get_instance()
        circuit = registry.get_or_create(
            f"simple-{config.name}",
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout_seconds=60.0,
            ),
        )

        # Create the agent node function with resilience
        async def agent_node(state: SimpleState) -> dict:
            """Agent node that calls the LLM with timeout and circuit breaker."""
            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await circuit.call(
                with_timeout(
                    llm.ainvoke(messages),
                    timeout_seconds=config.timeout_seconds,
                    operation="simple_agent LLM call",
                )
            )
            return {"messages": [response]}

        # Build the graph
        workflow = StateGraph(SimpleState)
        workflow.add_node("agent", agent_node)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)

        graph = workflow.compile()

        # Execute the graph with retry
        inputs: SimpleState = {
            "messages": [HumanMessage(content=user_prompt)]
        }

        async def execute_graph():
            return await graph.ainvoke(inputs)

        try:
            result = await retry_with_backoff(
                coro_factory=execute_graph,
                max_retries=3,
                backoff_config=DEFAULT_BACKOFF_CONFIG,
                retryable_exceptions=RETRYABLE_EXCEPTIONS,
                operation_name="simple_agent pipeline",
            )
        except BackoffExhaustedError as e:
            logger.error(f"Simple agent pipeline failed after retries: {e}")
            # Return fallback response
            return "I apologize, but I'm currently experiencing technical difficulties. Please try again.", 0
        except CircuitOpenError as e:
            logger.error(f"Circuit breaker open for simple agent: {e}")
            return "Service temporarily unavailable. Please try again in a moment.", 0

        # Extract response
        response_message = result["messages"][-1]
        response_text = response_message.content

        # Get token usage if available
        tokens_used = self._extract_tokens(response_message)

        logger.debug(f"LangGraph execution complete, tokens: {tokens_used}")

        return response_text, tokens_used

    async def run_multi_agent(
        self,
        config: LLMConfig,
        agent_configs: dict[AgentType, AgentConfig],
        user_prompt: str,
        context: dict[str, Any] | None = None,
        needs_moderation: bool = True,
        max_retries: int = 3,
    ) -> tuple[str, int, AgentType]:
        """Run the multi-agent LangGraph pipeline.

        Args:
            config: Default LLM configuration entity.
            agent_configs: Dictionary of agent configurations by type.
            user_prompt: User prompt text.
            context: Optional context for agent routing.
            needs_moderation: Whether to perform moderation check.
            max_retries: Maximum number of retries on failure.

        Returns:
            Tuple of (response text, tokens used, agent type used).
        """
        logger.info("Starting multi-agent pipeline execution")

        # Build the multi-agent workflow
        workflow = self._build_multi_agent_workflow(config, agent_configs)

        # Compile the graph
        graph = workflow.compile()

        # Create initial state
        initial_state = create_initial_state(
            user_message=user_prompt,
            agent_type=AgentType.MAIN.value,
            context=context,
            needs_moderation=needs_moderation,
        )

        # Define the graph execution function for retry wrapper
        async def execute_graph():
            return await graph.ainvoke(initial_state)

        # Execute the graph with backoff retry
        try:
            result = await retry_with_backoff(
                coro_factory=execute_graph,
                max_retries=max_retries,
                backoff_config=DEFAULT_BACKOFF_CONFIG,
                retryable_exceptions=RETRYABLE_EXCEPTIONS,
                operation_name="multi_agent pipeline",
            )
        except BackoffExhaustedError as e:
            logger.error(f"Multi-agent pipeline failed after {e.attempts} attempts: {e}")
            # Return fallback response
            return (
                "I apologize, but I'm currently experiencing technical difficulties. "
                "Please try again in a moment or contact support if the issue persists.",
                0,
                AgentType.FALLBACK,
            )
        except CircuitOpenError as e:
            logger.error(f"Circuit breaker open for multi-agent: {e}")
            return (
                "Service temporarily unavailable due to repeated failures. "
                "Please try again later.",
                0,
                AgentType.FALLBACK,
            )

        # Extract final response
        final_response = result.get("final_response")
        if not final_response and result.get("messages"):
            final_response = result["messages"][-1].content

        # Get the agent type that was used
        agent_type_used = AgentType(result.get("agent_type", AgentType.MAIN.value))

        # Get token usage
        tokens_used = 0
        if result.get("messages"):
            last_message = result["messages"][-1]
            tokens_used = self._extract_tokens(last_message)

        logger.info(f"Multi-agent pipeline complete, agent: {agent_type_used.value}, tokens: {tokens_used}")

        return final_response or "", tokens_used, agent_type_used

    def _build_multi_agent_workflow(
        self,
        default_config: LLMConfig,
        agent_configs: dict[AgentType, AgentConfig],
    ) -> StateGraph:
        """Build the multi-agent workflow graph.

        Args:
            default_config: Default LLM configuration to use.
            agent_configs: Dictionary of agent configurations.

        Returns:
            Compiled StateGraph for the multi-agent workflow.
        """
        # Get agent configurations or use defaults
        main_config = agent_configs.get(AgentType.MAIN)
        fallback_config = agent_configs.get(AgentType.FALLBACK)
        followup_config = agent_configs.get(AgentType.FOLLOWUP)
        moderation_config = agent_configs.get(AgentType.MODERATION)

        # Build node functions
        moderation_func = moderation_node(
            llm_config=default_config,
            system_prompt=moderation_config.system_prompt if moderation_config else
                "You are a content moderation assistant. Analyze messages for policy violations.",
        )

        router_func = router_node()

        main_func = main_agent_node(
            llm_config=default_config,
            system_prompt=main_config.system_prompt if main_config else
                "You are a helpful AI assistant.",
        )

        fallback_func = fallback_agent_node(
            llm_config=default_config,
            system_prompt=fallback_config.system_prompt if fallback_config else
                "You are a backup assistant providing simple, safe responses.",
        )

        followup_func = followup_agent_node(
            llm_config=default_config,
            system_prompt=followup_config.system_prompt if followup_config else
                "You are a conversational assistant helping with follow-up questions.",
        )

        # Create the workflow
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("moderation", moderation_func)
        workflow.add_node("router", router_func)
        workflow.add_node("main_agent", main_func)
        workflow.add_node("fallback_agent", fallback_func)
        workflow.add_node("followup_agent", followup_func)

        # Set entry point
        workflow.set_entry_point("moderation")

        # Add edges
        workflow.add_edge("moderation", "router")

        # Conditional routing from router
        workflow.add_conditional_edges(
            "router",
            self._route_after_router,
            {
                "main": "main_agent",
                "fallback": "fallback_agent",
                "followup": "followup_agent",
            },
        )

        # Conditional edges from main agent
        workflow.add_conditional_edges(
            "main_agent",
            self._route_after_main,
            {
                "success": END,
                "fallback": "fallback_agent",
            },
        )

        # All other agents go to END
        workflow.add_edge("fallback_agent", END)
        workflow.add_edge("followup_agent", END)

        return workflow

    def _route_after_router(self, state: AgentState) -> Literal["main", "fallback", "followup"]:
        """Determine which agent to route to after the router.

        Args:
            state: Current agent state.

        Returns:
            The next node to route to.
        """
        agent_type = state.get("agent_type", AgentType.MAIN.value)

        if agent_type == AgentType.FALLBACK.value:
            return "fallback"
        elif agent_type == AgentType.FOLLOWUP.value:
            return "followup"
        else:
            return "main"

    def _route_after_main(self, state: AgentState) -> Literal["success", "fallback"]:
        """Determine whether to succeed or fallback after main agent.

        Args:
            state: Current agent state.

        Returns:
            The next node to route to.
        """
        # Check for circuit breaker open - immediate fallback
        if state.get("circuit_open"):
            logger.warning("Circuit breaker open, routing to fallback")
            return "fallback"

        # Check for errors
        if state.get("error"):
            retry_count = state.get("retry_count", 0)
            if retry_count < 3:  # Max retries
                logger.info(f"Main agent failed, routing to fallback (retry {retry_count})")
                return "fallback"

        # Check if we have a response
        if state.get("final_response"):
            return "success"

        # Default to fallback if no response
        return "fallback"

    async def run_with_history(
        self,
        config: LLMConfig,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> tuple[str, int]:
        """Run the LangGraph pipeline with conversation history (backward compatible).

        Args:
            config: LLM configuration entity.
            system_prompt: System prompt text.
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            Tuple of (response text, tokens used).
        """
        from llm_worker.infrastructure.llm.agent_state import AgentState as SimpleState

        llm = LLMFactory.create(config)

        # Get circuit breaker for this LLM config
        registry = CircuitBreakerRegistry.get_instance()
        circuit = registry.get_or_create(
            f"history-{config.name}",
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout_seconds=60.0,
            ),
        )

        async def agent_node(state: SimpleState) -> dict:
            messages_with_system = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await circuit.call(
                with_timeout(
                    llm.ainvoke(messages_with_system),
                    timeout_seconds=config.timeout_seconds,
                    operation="history_agent LLM call",
                )
            )
            return {"messages": [response]}

        workflow = StateGraph(SimpleState)
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

        inputs: SimpleState = {"messages": langchain_messages}

        # Execute with retry
        async def execute_graph():
            return await graph.ainvoke(inputs)

        try:
            result = await retry_with_backoff(
                coro_factory=execute_graph,
                max_retries=3,
                backoff_config=DEFAULT_BACKOFF_CONFIG,
                retryable_exceptions=RETRYABLE_EXCEPTIONS,
                operation_name="history_agent pipeline",
            )
        except (BackoffExhaustedError, CircuitOpenError) as e:
            logger.error(f"History agent pipeline failed: {e}")
            return "I apologize, but I'm currently experiencing technical difficulties. Please try again.", 0

        response_message = result["messages"][-1]
        response_text = response_message.content

        tokens_used = self._extract_tokens(response_message)

        return response_text, tokens_used

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
