"""Abstract PromptTemplate repository interface."""
from abc import ABC, abstractmethod

from ai_engine.domain.entities import PromptTemplate


class PromptTemplateRepository(ABC):
    """Abstract repository interface for PromptTemplate aggregate."""

    @abstractmethod
    async def get_by_name(self, name: str) -> PromptTemplate | None:
        """Retrieve a prompt template by its unique name.

        Args:
            name: The unique name of the template.

        Returns:
            The PromptTemplate aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_all(self) -> list[PromptTemplate]:
        """Retrieve all prompt templates.

        Returns:
            List of all PromptTemplate aggregates.
        """
        pass

    @abstractmethod
    async def save(self, template: PromptTemplate) -> PromptTemplate:
        """Persist a PromptTemplate aggregate.

        Args:
            template: The template to persist.

        Returns:
            The persisted template.
        """
        pass

    @abstractmethod
    async def delete(self, name: str) -> bool:
        """Delete a prompt template by name.

        Args:
            name: The name of the template to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass
