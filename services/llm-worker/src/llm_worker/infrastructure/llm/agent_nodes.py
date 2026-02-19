"""Individual agent node implementations for multi-agent LangGraph workflows."""
import json
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm_worker.domain.entities import AgentType, LLMConfig
from llm_worker.infrastructure.llm.agent_state import AgentState
from llm_worker.infrastructure.llm.backoff import BackoffConfig
from llm_worker.infrastructure.llm.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitOpenError,
)
from llm_worker.infrastructure.llm.llm_factory import LLMFactory
from llm_worker.infrastructure.llm.response_validator import validate_response
from llm_worker.infrastructure.llm.timeout import LLMTimeoutError, with_timeout

logger = logging.getLogger(__name__)

# Default circuit breaker configuration for LLM calls
DEFAULT_CIRCUIT_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=2,
    timeout_seconds=60.0,
)

# Default moderation thresholds
MODERATION_CATEGORIES = [
    "harassment",
    "hate",
    "self_harm",
    "sexual",
    "violence",
    "spam",
]


def moderation_node(
    llm_config: LLMConfig,
    system_prompt: str,
) -> callable:
    """Create a moderation node that checks content for policy violations.

    Args:
        llm_config: LLM configuration to use for moderation.
        system_prompt: System prompt for the moderation agent.

    Returns:
        Async function that performs moderation check.
    """

    async def node(state: AgentState) -> dict[str, Any]:
        """Check message content for policy violations."""
        if not state.get("needs_moderation", True):
            logger.debug("Skipping moderation as not needed")
            return {"needs_moderation": False, "moderation_result": None}

        # Get the last user message
        user_message = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                user_message = msg.content
                break

        if not user_message:
            return {"needs_moderation": False, "moderation_result": None}

        try:
            llm = LLMFactory.create(llm_config)

            # Build moderation prompt
            prompt = f"""Analyze the following message for content policy violations.
Check for: {', '.join(MODERATION_CATEGORIES)}.

Message to analyze: "{user_message}"

Respond in JSON format with:
{{
    "is_safe": true/false,
    "violations": ["list of violation categories if any"],
    "confidence": 0.0-1.0,
    "reason": "brief explanation if not safe"
}}"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ]

            # Get circuit breaker for this LLM config
            registry = CircuitBreakerRegistry.get_instance()
            circuit = registry.get_or_create(
                f"moderation-{llm_config.name}",
                DEFAULT_CIRCUIT_BREAKER_CONFIG,
            )

            # Execute with timeout and circuit breaker
            response = await circuit.call(
                with_timeout(
                    llm.ainvoke(messages),
                    timeout_seconds=llm_config.timeout_seconds,
                    operation="moderation LLM call",
                )
            )
            response_text = response.content

            # Parse JSON response
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Default to safe if parsing fails
                result = {"is_safe": True, "violations": [], "confidence": 0.5, "reason": "Unable to parse"}

            logger.info(f"Moderation result: is_safe={result.get('is_safe', True)}")

            return {
                "needs_moderation": False,
                "moderation_result": result,
            }

        except Exception as e:
            logger.error(f"Moderation failed: {e}")
            # On error, allow content through but log the issue
            return {
                "needs_moderation": False,
                "moderation_result": {
                    "is_safe": True,
                    "violations": [],
                    "confidence": 0.0,
                    "reason": f"Moderation check failed: {str(e)}",
                },
            }

    return node


def router_node() -> callable:
    """Create a router node that determines which agent should handle the message.

    Returns:
        Async function that routes to the appropriate agent.
    """

    async def node(state: AgentState) -> dict[str, Any]:
        """Determine the appropriate agent for the message."""
        # If moderation found violations, route to fallback
        moderation_result = state.get("moderation_result")
        if moderation_result and not moderation_result.get("is_safe", True):
            logger.info("Routing to fallback due to moderation violation")
            return {"agent_type": AgentType.FALLBACK.value}

        # Check if this looks like a follow-up question
        context = state.get("context", {})
        if context.get("is_followup", False):
            logger.info("Routing to followup agent")
            return {"agent_type": AgentType.FOLLOWUP.value}

        # Check message content for follow-up indicators
        last_message = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_message = msg.content.lower()
                break

        if last_message:
            followup_indicators = [
                "what about",
                "can you explain",
                "tell me more",
                "and then",
                "what else",
                "continue",
                "go on",
                "more details",
                "elaborate",
            ]
            if any(indicator in last_message for indicator in followup_indicators):
                logger.info("Follow-up indicators detected, routing to followup agent")
                return {"agent_type": AgentType.FOLLOWUP.value}

        # Default to main agent
        logger.debug("Routing to main agent")
        return {"agent_type": AgentType.MAIN.value}

    return node


def main_agent_node(
    llm_config: LLMConfig,
    system_prompt: str,
) -> callable:
    """Create the main agent node for primary response handling.

    Args:
        llm_config: LLM configuration to use.
        system_prompt: System prompt for the main agent.

    Returns:
        Async function that processes messages with the main agent.
    """

    async def node(state: AgentState) -> dict[str, Any]:
        """Process message with the main agent."""
        logger.info("Processing with main agent")

        try:
            llm = LLMFactory.create(llm_config)

            # Build messages with context
            context = state.get("context", {})
            enhanced_prompt = system_prompt

            if context:
                context_str = json.dumps(context, indent=2)
                enhanced_prompt = f"{system_prompt}\n\nAdditional context:\n{context_str}"

            messages = [SystemMessage(content=enhanced_prompt)] + state["messages"]

            # Get circuit breaker for this LLM config
            registry = CircuitBreakerRegistry.get_instance()
            circuit = registry.get_or_create(
                f"main-{llm_config.name}",
                DEFAULT_CIRCUIT_BREAKER_CONFIG,
            )

            # Execute with timeout and circuit breaker
            response = await circuit.call(
                with_timeout(
                    llm.ainvoke(messages),
                    timeout_seconds=llm_config.timeout_seconds,
                    operation="main_agent LLM call",
                )
            )
            response_message = response

            # Extract response and token usage
            response_text = response_message.content
            tokens_used = _extract_tokens(response_message)

            # Validate response quality
            validation = validate_response(response_text)
            if not validation.is_valid:
                logger.warning(f"Main agent response validation failed: {validation.reason}")
                return {
                    "error": f"Invalid response: {validation.reason}",
                    "retry_count": state.get("retry_count", 0) + 1,
                }

            logger.info(f"Main agent response generated, tokens: {tokens_used}")

            return {
                "messages": [response_message],
                "final_response": response_text,
                "error": None,
            }

        except LLMTimeoutError as e:
            logger.error(f"Main agent timed out: {e}")
            return {
                "error": str(e),
                "retry_count": state.get("retry_count", 0) + 1,
            }
        except CircuitOpenError as e:
            logger.error(f"Main agent circuit breaker open: {e}")
            return {
                "error": f"Service temporarily unavailable: {e}",
                "retry_count": state.get("retry_count", 0) + 1,
                "circuit_open": True,
            }
        except Exception as e:
            logger.error(f"Main agent failed: {e}")
            return {
                "error": str(e),
                "retry_count": state.get("retry_count", 0) + 1,
            }

    return node


def fallback_agent_node(
    llm_config: LLMConfig,
    system_prompt: str,
) -> callable:
    """Create the fallback agent node for backup response handling.

    Args:
        llm_config: LLM configuration to use.
        system_prompt: System prompt for the fallback agent.

    Returns:
        Async function that processes messages with the fallback agent.
    """

    async def node(state: AgentState) -> dict[str, Any]:
        """Process message with the fallback agent."""
        logger.info("Processing with fallback agent")

        # Check if this is a moderation violation
        moderation_result = state.get("moderation_result")
        if moderation_result and not moderation_result.get("is_safe", True):
            violations = moderation_result.get("violations", [])
            response_text = (
                "I apologize, but I'm unable to process this request as it may "
                "violate content policies. Please rephrase your question and try again."
            )
            logger.info(f"Fallback agent handling moderation violation: {violations}")
            return {
                "final_response": response_text,
                "error": None,
            }

        # Handle main agent failure
        try:
            llm = LLMFactory.create(llm_config)

            # Use simpler prompt for fallback
            fallback_prompt = f"""You are a helpful assistant providing a backup response.
If the previous response was incomplete or had issues, provide a simpler, more direct answer.

User's original question or request needs a straightforward response."""

            messages = [
                SystemMessage(content=system_prompt),
                SystemMessage(content=fallback_prompt),
            ] + state["messages"]

            # Get circuit breaker for this LLM config
            registry = CircuitBreakerRegistry.get_instance()
            circuit = registry.get_or_create(
                f"fallback-{llm_config.name}",
                DEFAULT_CIRCUIT_BREAKER_CONFIG,
            )

            # Execute with timeout and circuit breaker
            response = await circuit.call(
                with_timeout(
                    llm.ainvoke(messages),
                    timeout_seconds=llm_config.timeout_seconds,
                    operation="fallback_agent LLM call",
                )
            )
            response_text = response.content

            logger.info("Fallback agent response generated")

            return {
                "messages": [response],
                "final_response": response_text,
                "error": None,
            }

        except (LLMTimeoutError, CircuitOpenError) as e:
            logger.error(f"Fallback agent failed: {e}")
            # Ultimate fallback - return a static response
            return {
                "final_response": (
                    "I apologize, but I'm currently experiencing technical difficulties. "
                    "Please try again in a moment or contact support if the issue persists."
                ),
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Fallback agent failed: {e}")
            # Ultimate fallback - return a static response
            return {
                "final_response": (
                    "I apologize, but I'm currently experiencing technical difficulties. "
                    "Please try again in a moment or contact support if the issue persists."
                ),
                "error": str(e),
            }

    return node


def followup_agent_node(
    llm_config: LLMConfig,
    system_prompt: str,
) -> callable:
    """Create the followup agent node for conversation continuity.

    Args:
        llm_config: LLM configuration to use.
        system_prompt: System prompt for the followup agent.

    Returns:
        Async function that processes messages with the followup agent.
    """

    async def node(state: AgentState) -> dict[str, Any]:
        """Process message with the followup agent."""
        logger.info("Processing with followup agent")

        try:
            llm = LLMFactory.create(llm_config)

            # Build context-aware prompt for follow-up
            context = state.get("context", {})
            enhanced_prompt = system_prompt

            if context.get("previous_topic"):
                enhanced_prompt += f"\n\nThe previous conversation was about: {context['previous_topic']}"

            # Include conversation history for context
            messages = [SystemMessage(content=enhanced_prompt)] + state["messages"]

            # Get circuit breaker for this LLM config
            registry = CircuitBreakerRegistry.get_instance()
            circuit = registry.get_or_create(
                f"followup-{llm_config.name}",
                DEFAULT_CIRCUIT_BREAKER_CONFIG,
            )

            # Execute with timeout and circuit breaker
            response = await circuit.call(
                with_timeout(
                    llm.ainvoke(messages),
                    timeout_seconds=llm_config.timeout_seconds,
                    operation="followup_agent LLM call",
                )
            )
            response_text = response.content

            # Validate response quality
            validation = validate_response(response_text)
            if not validation.is_valid:
                logger.warning(f"Followup agent response validation failed: {validation.reason}")
                return {
                    "error": f"Invalid response: {validation.reason}",
                    "retry_count": state.get("retry_count", 0) + 1,
                }

            tokens_used = _extract_tokens(response)

            logger.info(f"Followup agent response generated, tokens: {tokens_used}")

            return {
                "messages": [response],
                "final_response": response_text,
                "error": None,
            }

        except LLMTimeoutError as e:
            logger.error(f"Followup agent timed out: {e}")
            return {
                "error": str(e),
                "retry_count": state.get("retry_count", 0) + 1,
            }
        except CircuitOpenError as e:
            logger.error(f"Followup agent circuit breaker open: {e}")
            return {
                "error": f"Service temporarily unavailable: {e}",
                "retry_count": state.get("retry_count", 0) + 1,
                "circuit_open": True,
            }
        except Exception as e:
            logger.error(f"Followup agent failed: {e}")
            return {
                "error": str(e),
                "retry_count": state.get("retry_count", 0) + 1,
            }

    return node


def _extract_tokens(message: AIMessage) -> int:
    """Extract token usage from an AI message.

    Args:
        message: The AI message to extract tokens from.

    Returns:
        Number of tokens used, or 0 if not available.
    """
    if hasattr(message, "response_metadata"):
        metadata = message.response_metadata
        if "token_usage" in metadata:
            return metadata["token_usage"].get("total_tokens", 0)
    return 0
