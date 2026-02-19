"""Agent configuration entity and types."""
from dataclasses import dataclass, field
from enum import Enum


class AgentType(str, Enum):
    """Types of agents in the multi-agent system."""

    MAIN = "main"
    FALLBACK = "fallback"
    FOLLOWUP = "followup"
    MODERATION = "moderation"

    @property
    def is_main(self) -> bool:
        """Check if this is the main agent."""
        return self == AgentType.MAIN

    @property
    def is_fallback(self) -> bool:
        """Check if this is the fallback agent."""
        return self == AgentType.FALLBACK

    @property
    def is_followup(self) -> bool:
        """Check if this is the followup agent."""
        return self == AgentType.FOLLOWUP

    @property
    def is_moderation(self) -> bool:
        """Check if this is the moderation agent."""
        return self == AgentType.MODERATION


@dataclass
class AgentConfig:
    """Configuration for a specific agent in the multi-agent system.

    Defines the behavior and settings for each agent type including
    system prompts, LLM configuration, and processing parameters.
    """
    _agent_type: AgentType
    _system_prompt: str
    _llm_config_name: str = "default-smart"
    _temperature: float = 0.7
    _max_tokens: int = 4096
    _max_retries: int = 2
    _timeout_seconds: int = 60
    _enabled: bool = True

    @property
    def agent_type(self) -> AgentType:
        """Get the agent type."""
        return self._agent_type

    @property
    def system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return self._system_prompt

    @property
    def llm_config_name(self) -> str:
        """Get the LLM configuration name to use."""
        return self._llm_config_name

    @property
    def temperature(self) -> float:
        """Get the temperature setting."""
        return self._temperature

    @property
    def max_tokens(self) -> int:
        """Get the max tokens setting."""
        return self._max_tokens

    @property
    def max_retries(self) -> int:
        """Get the maximum retry attempts."""
        return self._max_retries

    @property
    def timeout_seconds(self) -> int:
        """Get the timeout in seconds."""
        return self._timeout_seconds

    @property
    def enabled(self) -> bool:
        """Check if this agent is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable this agent."""
        self._enabled = True

    def disable(self) -> None:
        """Disable this agent."""
        self._enabled = False

    def update_system_prompt(self, prompt: str) -> None:
        """Update the system prompt."""
        if not prompt or not prompt.strip():
            raise ValueError("System prompt cannot be empty")
        self._system_prompt = prompt.strip()

    def update_temperature(self, temperature: float) -> None:
        """Update the temperature setting."""
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        self._temperature = temperature

    def update_max_tokens(self, max_tokens: int) -> None:
        """Update the max tokens setting."""
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        self._max_tokens = max_tokens

    @classmethod
    def create(
        cls,
        agent_type: AgentType,
        system_prompt: str,
        llm_config_name: str = "default-smart",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_retries: int = 2,
        timeout_seconds: int = 60,
    ) -> "AgentConfig":
        """Factory method to create a new AgentConfig.

        Args:
            agent_type: The type of agent.
            system_prompt: The system prompt for this agent.
            llm_config_name: Name of the LLM config to use.
            temperature: Temperature for response generation.
            max_tokens: Maximum tokens in response.
            max_retries: Maximum retry attempts.
            timeout_seconds: Timeout for LLM calls.

        Returns:
            A new AgentConfig instance.
        """
        if not system_prompt or not system_prompt.strip():
            raise ValueError("System prompt cannot be empty")
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")

        return cls(
            _agent_type=agent_type,
            _system_prompt=system_prompt.strip(),
            _llm_config_name=llm_config_name,
            _temperature=temperature,
            _max_tokens=max_tokens,
            _max_retries=max_retries,
            _timeout_seconds=timeout_seconds,
            _enabled=True,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "agent_type": self._agent_type.value,
            "system_prompt": self._system_prompt,
            "llm_config_name": self._llm_config_name,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "max_retries": self._max_retries,
            "timeout_seconds": self._timeout_seconds,
            "enabled": self._enabled,
        }
