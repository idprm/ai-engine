"""Tenant controller for CRM API endpoints.

This controller handles tenant management operations that were migrated
from the Commerce Agent service.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from commerce_agent.application.dto import CreateTenantDTO, TenantDTO, UpdateTenantDTO
from commerce_agent.domain.repositories import TenantRepository
from commerce_agent.domain.entities import Tenant
from commerce_agent.domain.value_objects import TenantId
from gateway.crm.dependencies import get_tenant_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post("/", response_model=TenantDTO, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    dto: CreateTenantDTO,
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantDTO:
    """Create a new tenant (business)."""
    tenant = Tenant.create(
        name=dto.name,
        wa_session=dto.wa_session,
        llm_config_name=dto.llm_config_name,
        agent_prompt=dto.agent_prompt,
        payment_provider=dto.payment_provider,
        payment_config=dto.payment_config,
        business_hours=dto.business_hours,
    )

    tenant = await tenant_repository.save(tenant)

    return TenantDTO(
        id=str(tenant.id),
        name=tenant.name,
        wa_session=tenant.wa_session,
        llm_config_name=tenant.llm_config_name,
        agent_prompt=tenant.agent_prompt,
        payment_provider=tenant.payment_provider,
        payment_config=tenant.payment_config,
        business_hours=tenant.business_hours,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


@router.get("/{tenant_id}", response_model=TenantDTO)
async def get_tenant(
    tenant_id: str,
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantDTO:
    """Get tenant by ID."""
    tenant = await tenant_repository.get_by_id(TenantId.from_string(tenant_id))

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found: {tenant_id}",
        )

    return TenantDTO(
        id=str(tenant.id),
        name=tenant.name,
        wa_session=tenant.wa_session,
        llm_config_name=tenant.llm_config_name,
        agent_prompt=tenant.agent_prompt,
        payment_provider=tenant.payment_provider,
        payment_config=tenant.payment_config,
        business_hours=tenant.business_hours,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


@router.get("/", response_model=list[TenantDTO])
async def list_tenants(
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> list[TenantDTO]:
    """List all tenants."""
    tenants = await tenant_repository.list_all()

    return [
        TenantDTO(
            id=str(t.id),
            name=t.name,
            wa_session=t.wa_session,
            llm_config_name=t.llm_config_name,
            agent_prompt=t.agent_prompt,
            payment_provider=t.payment_provider,
            payment_config=t.payment_config,
            business_hours=t.business_hours,
            is_active=t.is_active,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tenants
    ]


@router.put("/{tenant_id}", response_model=TenantDTO)
async def update_tenant(
    tenant_id: str,
    dto: UpdateTenantDTO,
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantDTO:
    """Update tenant."""
    tenant = await tenant_repository.get_by_id(TenantId.from_string(tenant_id))

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found: {tenant_id}",
        )

    if dto.name is not None:
        tenant._name = dto.name
    if dto.agent_prompt is not None:
        tenant.update_agent_prompt(dto.agent_prompt)
    if dto.payment_config is not None:
        tenant.update_payment_config(dto.payment_config)
    if dto.business_hours is not None:
        tenant.update_business_hours(dto.business_hours)
    if dto.is_active is not None:
        if dto.is_active:
            tenant.activate()
        else:
            tenant.deactivate()

    tenant = await tenant_repository.save(tenant)

    return TenantDTO(
        id=str(tenant.id),
        name=tenant.name,
        wa_session=tenant.wa_session,
        llm_config_name=tenant.llm_config_name,
        agent_prompt=tenant.agent_prompt,
        payment_provider=tenant.payment_provider,
        payment_config=tenant.payment_config,
        business_hours=tenant.business_hours,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


@router.put("/{tenant_id}/prompt", response_model=TenantDTO)
async def update_agent_prompt(
    tenant_id: str,
    prompt: str,
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantDTO:
    """Update tenant's AI agent prompt."""
    tenant = await tenant_repository.get_by_id(TenantId.from_string(tenant_id))

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found: {tenant_id}",
        )

    tenant.update_agent_prompt(prompt)
    tenant = await tenant_repository.save(tenant)

    return TenantDTO(
        id=str(tenant.id),
        name=tenant.name,
        wa_session=tenant.wa_session,
        llm_config_name=tenant.llm_config_name,
        agent_prompt=tenant.agent_prompt,
        payment_provider=tenant.payment_provider,
        payment_config=tenant.payment_config,
        business_hours=tenant.business_hours,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> None:
    """Delete tenant."""
    deleted = await tenant_repository.delete(TenantId.from_string(tenant_id))

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found: {tenant_id}",
        )
