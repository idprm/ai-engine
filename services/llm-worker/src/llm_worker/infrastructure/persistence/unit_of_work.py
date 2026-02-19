"""Unit of Work pattern implementation."""
from typing import Protocol

from llm_worker.domain.repositories import LLMConfigRepository, PromptTemplateRepository


class UnitOfWork(Protocol):
    """Unit of Work protocol."""

    llm_configs: LLMConfigRepository
    prompt_templates: PromptTemplateRepository

    async def __aenter__(self):
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ...

    async def commit(self):
        ...

    async def rollback(self):
        ...


class SQLAlchemyUnitOfWork:
    """SQLAlchemy implementation of Unit of Work."""

    def __init__(self, session_factory=None):
        from llm_worker.infrastructure.persistence.database import AsyncSessionLocal
        self._session_factory = session_factory or AsyncSessionLocal
        self._session = None
        self.llm_configs = None
        self.prompt_templates = None

    async def __aenter__(self):
        from llm_worker.infrastructure.persistence.llm_config_repository_impl import LLMConfigRepositoryImpl
        from llm_worker.infrastructure.persistence.prompt_template_repository_impl import PromptTemplateRepositoryImpl

        self._session = self._session_factory()
        self.llm_configs = LLMConfigRepositoryImpl()
        self.prompt_templates = PromptTemplateRepositoryImpl()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        await self._session.close()

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()
