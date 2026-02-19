"""Ticket repository interfaces."""
from abc import ABC, abstractmethod

from commerce_agent.domain.entities import Ticket, TicketBoard, TicketTemplate
from commerce_agent.domain.value_objects import TicketId, TenantId, TicketStatus, TicketPriority


class TicketRepository(ABC):
    """Abstract repository interface for Ticket aggregate."""

    @abstractmethod
    async def get_by_id(self, ticket_id: TicketId) -> Ticket | None:
        """Retrieve a ticket by its unique identifier."""
        pass

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        assignee_id: str | None = None,
        board_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Ticket]:
        """List tickets for a tenant with optional filters."""
        pass

    @abstractmethod
    async def list_by_customer(
        self,
        customer_id: str,
        active_only: bool = True,
    ) -> list[Ticket]:
        """List tickets for a customer."""
        pass

    @abstractmethod
    async def list_by_conversation(
        self,
        conversation_id: str,
    ) -> list[Ticket]:
        """List tickets for a conversation."""
        pass

    @abstractmethod
    async def list_by_assignee(
        self,
        assignee_id: str,
        active_only: bool = True,
    ) -> list[Ticket]:
        """List tickets assigned to an agent."""
        pass

    @abstractmethod
    async def count_by_status(
        self,
        tenant_id: TenantId,
        status: TicketStatus | None = None,
    ) -> int:
        """Count tickets by status."""
        pass

    @abstractmethod
    async def save(self, ticket: Ticket) -> Ticket:
        """Persist a ticket aggregate."""
        pass

    @abstractmethod
    async def delete(self, ticket_id: TicketId) -> bool:
        """Delete a ticket."""
        pass


class TicketBoardRepository(ABC):
    """Abstract repository interface for TicketBoard entity."""

    @abstractmethod
    async def get_by_id(self, board_id: str) -> TicketBoard | None:
        """Retrieve a board by ID."""
        pass

    @abstractmethod
    async def list_by_tenant(self, tenant_id: TenantId) -> list[TicketBoard]:
        """List all boards for a tenant."""
        pass

    @abstractmethod
    async def get_default_board(self, tenant_id: TenantId) -> TicketBoard | None:
        """Get the default board for a tenant."""
        pass

    @abstractmethod
    async def save(self, board: TicketBoard) -> TicketBoard:
        """Persist a board."""
        pass

    @abstractmethod
    async def delete(self, board_id: str) -> bool:
        """Delete a board."""
        pass


class TicketTemplateRepository(ABC):
    """Abstract repository interface for TicketTemplate entity."""

    @abstractmethod
    async def get_by_id(self, template_id: str) -> TicketTemplate | None:
        """Retrieve a template by ID."""
        pass

    @abstractmethod
    async def list_by_tenant(self, tenant_id: TenantId) -> list[TicketTemplate]:
        """List all templates for a tenant."""
        pass

    @abstractmethod
    async def save(self, template: TicketTemplate) -> TicketTemplate:
        """Persist a template."""
        pass

    @abstractmethod
    async def delete(self, template_id: str) -> bool:
        """Delete a template."""
        pass
