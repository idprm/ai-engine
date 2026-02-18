"""Unit of Work pattern implementation."""
from typing import Protocol

from gateway.domain.repositories import JobRepository


class UnitOfWork(Protocol):
    """Unit of Work protocol for managing transactions."""

    jobs: JobRepository

    async def __aenter__(self):
        """Enter the unit of work context."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the unit of work context, committing or rolling back."""
        ...

    async def commit(self):
        """Commit the current transaction."""
        ...

    async def rollback(self):
        """Rollback the current transaction."""
        ...


class SQLAlchemyUnitOfWork:
    """SQLAlchemy implementation of Unit of Work."""

    def __init__(self, session_factory=None):
        from gateway.infrastructure.persistence.database import AsyncSessionLocal
        self._session_factory = session_factory or AsyncSessionLocal
        self._session = None
        self.jobs = None

    async def __aenter__(self):
        from gateway.infrastructure.persistence.job_repository_impl import JobRepositoryImpl
        self._session = self._session_factory()
        self.jobs = JobRepositoryImpl()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self._session.close()

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()
