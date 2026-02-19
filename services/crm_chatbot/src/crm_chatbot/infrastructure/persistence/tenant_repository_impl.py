"""SQLAlchemy implementation of TenantRepository."""
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crm_chatbot.domain.entities import Tenant
from crm_chatbot.domain.repositories import TenantRepository
from crm_chatbot.domain.value_objects import TenantId
from crm_chatbot.infrastructure.persistence.database import get_db_session
from crm_chatbot.infrastructure.persistence.models import TenantModel

logger = logging.getLogger(__name__)


class TenantRepositoryImpl(TenantRepository):
    """SQLAlchemy implementation of TenantRepository."""

    async def get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieve a tenant by its unique identifier."""
        async with get_db_session() as session:
            result = await session.execute(
                select(TenantModel).where(TenantModel.id == tenant_id.value)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def get_by_wa_session(self, wa_session: str) -> Tenant | None:
        """Retrieve a tenant by its WhatsApp session name."""
        async with get_db_session() as session:
            result = await session.execute(
                select(TenantModel).where(TenantModel.wa_session == wa_session)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def save(self, tenant: Tenant) -> Tenant:
        """Persist a tenant aggregate."""
        async with get_db_session() as session:
            # Check if exists
            existing = await session.get(TenantModel, tenant.id.value)

            if existing:
                # Update existing
                existing.name = tenant.name
                existing.wa_session = tenant.wa_session
                existing.llm_config_name = tenant.llm_config_name
                existing.agent_prompt = tenant.agent_prompt
                existing.payment_provider = tenant.payment_provider
                existing.payment_config = tenant.payment_config
                existing.business_hours = tenant.business_hours
                existing.is_active = tenant.is_active
            else:
                # Create new
                model = self._to_model(tenant)
                session.add(model)

            await session.flush()
            return tenant

    async def list_active(self) -> list[Tenant]:
        """List all active tenants."""
        async with get_db_session() as session:
            result = await session.execute(
                select(TenantModel).where(TenantModel.is_active == True)
            )
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def delete(self, tenant_id: TenantId) -> bool:
        """Delete a tenant."""
        async with get_db_session() as session:
            model = await session.get(TenantModel, tenant_id.value)
            if model:
                await session.delete(model)
                return True
            return False

    def _to_entity(self, model: TenantModel) -> Tenant:
        """Convert SQLAlchemy model to domain entity."""
        # Create entity without triggering __post_init__ events
        tenant = Tenant.__new__(Tenant)
        tenant._id = TenantId(value=model.id)
        tenant._name = model.name
        tenant._wa_session = model.wa_session
        tenant._llm_config_name = model.llm_config_name
        tenant._agent_prompt = model.agent_prompt
        tenant._payment_provider = model.payment_provider
        tenant._payment_config = model.payment_config
        tenant._business_hours = model.business_hours
        tenant._is_active = model.is_active
        tenant._created_at = model.created_at
        tenant._updated_at = model.updated_at
        tenant._events = []
        return tenant

    def _to_model(self, entity: Tenant) -> TenantModel:
        """Convert domain entity to SQLAlchemy model."""
        return TenantModel(
            id=entity.id.value,
            name=entity.name,
            wa_session=entity.wa_session,
            llm_config_name=entity.llm_config_name,
            agent_prompt=entity.agent_prompt,
            payment_provider=entity.payment_provider,
            payment_config=entity.payment_config,
            business_hours=entity.business_hours,
            is_active=entity.is_active,
        )
