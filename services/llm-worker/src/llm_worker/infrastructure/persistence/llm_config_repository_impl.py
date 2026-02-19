"""LLMConfig repository implementation using SQLAlchemy."""
import logging

from sqlalchemy import select

from llm_worker.domain.entities import LLMConfig
from llm_worker.domain.repositories import LLMConfigRepository
from llm_worker.domain.value_objects import ModelName, Provider, Temperature
from llm_worker.infrastructure.persistence.database import get_db_session
from llm_worker.infrastructure.persistence.models import LLMConfigModel

logger = logging.getLogger(__name__)


class LLMConfigRepositoryImpl(LLMConfigRepository):
    """SQLAlchemy implementation of LLMConfigRepository."""

    async def get_by_name(self, name: str) -> LLMConfig | None:
        """Retrieve LLM config by name."""
        async with get_db_session() as session:
            stmt = select(LLMConfigModel).where(LLMConfigModel.name == name)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            return self._to_entity(model)

    async def get_all_active(self) -> list[LLMConfig]:
        """Retrieve all active LLM configurations."""
        async with get_db_session() as session:
            stmt = select(LLMConfigModel).where(LLMConfigModel.is_active == True)
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def save(self, config: LLMConfig) -> LLMConfig:
        """Persist LLM configuration."""
        async with get_db_session() as session:
            stmt = select(LLMConfigModel).where(LLMConfigModel.name == config.name)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model:
                model.provider = str(config.provider)
                model.model_name = str(config.model_name)
                model.temperature = float(config.temperature)
                model.max_tokens = config.max_tokens
                model.is_active = config.is_active
            else:
                model = LLMConfigModel(
                    name=config.name,
                    provider=str(config.provider),
                    model_name=str(config.model_name),
                    api_key_env=config.api_key_env,
                    temperature=float(config.temperature),
                    max_tokens=config.max_tokens,
                    is_active=config.is_active,
                )
                session.add(model)

            return config

    async def delete(self, name: str) -> bool:
        """Delete LLM config by name."""
        async with get_db_session() as session:
            stmt = select(LLMConfigModel).where(LLMConfigModel.name == name)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model:
                await session.delete(model)
                return True
            return False

    def _to_entity(self, model: LLMConfigModel) -> LLMConfig:
        """Convert ORM model to domain entity."""
        return LLMConfig(
            _name=model.name,
            _provider=Provider(type=model.provider),
            _model_name=ModelName(value=model.model_name),
            _api_key_env=model.api_key_env,
            _temperature=Temperature(value=model.temperature),
            _max_tokens=model.max_tokens,
            _is_active=model.is_active,
        )
