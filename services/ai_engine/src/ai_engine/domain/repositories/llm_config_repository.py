"""Abstract LLMConfig repository interface."""
from abc import ABC, abstractmethod

from ai_engine.domain.entities import LLMConfig


class LLMConfigRepository(ABC):
    """Abstract repository interface for LLMConfig aggregate."""

    @abstractmethod
    async def get_by_name(self, name: str) -> LLMConfig | None:
        """Retrieve an LLM config by its unique name.

        Args:
            name: The unique name of the configuration.

        Returns:
            The LLMConfig aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_all_active(self) -> list[LLMConfig]:
        """Retrieve all active LLM configurations.

        Returns:
            List of active LLMConfig aggregates.
        """
        pass

    @abstractmethod
    async def save(self, config: LLMConfig) -> LLMConfig:
        """Persist an LLMConfig aggregate.

        Args:
            config: The configuration to persist.

        Returns:
            The persisted configuration.
        """
        pass

    @abstractmethod
    async def delete(self, name: str) -> bool:
        """Delete an LLM config by name.

        Args:
            name: The name of the configuration to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass
