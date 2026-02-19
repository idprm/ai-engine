"""PromptTemplate repository implementation using SQLAlchemy."""
import logging

from sqlalchemy import select

from llm_worker.domain.entities import PromptTemplate
from llm_worker.domain.repositories import PromptTemplateRepository
from llm_worker.infrastructure.persistence.database import get_db_session
from llm_worker.infrastructure.persistence.models import PromptTemplateModel

logger = logging.getLogger(__name__)


class PromptTemplateRepositoryImpl(PromptTemplateRepository):
    """SQLAlchemy implementation of PromptTemplateRepository."""

    async def get_by_name(self, name: str) -> PromptTemplate | None:
        """Retrieve prompt template by name."""
        async with get_db_session() as session:
            stmt = select(PromptTemplateModel).where(PromptTemplateModel.name == name)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            return self._to_entity(model)

    async def get_all(self) -> list[PromptTemplate]:
        """Retrieve all prompt templates."""
        async with get_db_session() as session:
            stmt = select(PromptTemplateModel)
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def save(self, template: PromptTemplate) -> PromptTemplate:
        """Persist prompt template."""
        async with get_db_session() as session:
            stmt = select(PromptTemplateModel).where(PromptTemplateModel.name == template.name)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model:
                model.content = template.content
                model.description = template.description
            else:
                model = PromptTemplateModel(
                    name=template.name,
                    content=template.content,
                    description=template.description,
                )
                session.add(model)

            return template

    async def delete(self, name: str) -> bool:
        """Delete prompt template by name."""
        async with get_db_session() as session:
            stmt = select(PromptTemplateModel).where(PromptTemplateModel.name == name)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model:
                await session.delete(model)
                return True
            return False

    def _to_entity(self, model: PromptTemplateModel) -> PromptTemplate:
        """Convert ORM model to domain entity."""
        return PromptTemplate(
            _name=model.name,
            _content=model.content,
            _description=model.description,
        )
