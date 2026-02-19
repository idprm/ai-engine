"""Product controller for CRM API endpoints.

This controller handles product management operations that were migrated
from the CRM chatbot service.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from commerce_agent.application.dto import (
    CreateProductDTO,
    ProductDTO,
    ProductVariantDTO,
    CreateProductVariantDTO,
)
from commerce_agent.domain.repositories import ProductRepository
from commerce_agent.domain.entities import Product, ProductVariant
from commerce_agent.domain.value_objects import ProductId, TenantId, Money
from gateway.crm.dependencies import get_product_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants/{tenant_id}/products", tags=["Products"])


@router.post("/", response_model=ProductDTO, status_code=status.HTTP_201_CREATED)
async def create_product(
    tenant_id: str,
    dto: CreateProductDTO,
    product_repository: ProductRepository = Depends(get_product_repository),
) -> ProductDTO:
    """Create a new product."""
    product = Product.create(
        tenant_id=TenantId.from_string(tenant_id),
        name=dto.name,
        description=dto.description or "",
        base_price=Money.from_float(dto.base_price),
        category=dto.category,
    )

    # Add variants
    for variant_dto in dto.variants:
        variant = ProductVariant.create(
            sku=variant_dto.sku,
            name=variant_dto.name,
            price=Money.from_float(variant_dto.price),
            stock=variant_dto.stock,
            attributes=variant_dto.attributes,
        )
        product.add_variant(variant)

    product = await product_repository.save(product)

    return _to_dto(product)


@router.get("/", response_model=list[ProductDTO])
async def list_products(
    tenant_id: str,
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
    product_repository: ProductRepository = Depends(get_product_repository),
) -> list[ProductDTO]:
    """List products for a tenant."""
    products = await product_repository.list_by_tenant(
        tenant_id=TenantId.from_string(tenant_id),
        category=category,
        active_only=active_only,
    )

    return [_to_dto(p) for p in products]


@router.get("/search", response_model=list[ProductDTO])
async def search_products(
    tenant_id: str,
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    product_repository: ProductRepository = Depends(get_product_repository),
) -> list[ProductDTO]:
    """Search products."""
    products = await product_repository.search(
        tenant_id=TenantId.from_string(tenant_id),
        query=q,
        category=category,
        min_price=int(min_price * 100) if min_price else None,
        max_price=int(max_price * 100) if max_price else None,
    )

    return [_to_dto(p) for p in products]


@router.get("/{product_id}", response_model=ProductDTO)
async def get_product(
    tenant_id: str,
    product_id: str,
    product_repository: ProductRepository = Depends(get_product_repository),
) -> ProductDTO:
    """Get product by ID."""
    product = await product_repository.get_by_id(
        ProductId.from_string(product_id)
    )

    if not product or str(product.tenant_id) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {product_id}",
        )

    return _to_dto(product)


@router.put("/{product_id}", response_model=ProductDTO)
async def update_product(
    tenant_id: str,
    product_id: str,
    dto: CreateProductDTO,
    product_repository: ProductRepository = Depends(get_product_repository),
) -> ProductDTO:
    """Update product."""
    product = await product_repository.get_by_id(
        ProductId.from_string(product_id)
    )

    if not product or str(product.tenant_id) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {product_id}",
        )

    product.update_info(
        name=dto.name,
        description=dto.description,
        category=dto.category,
    )

    # Update base price
    product._base_price = Money.from_float(dto.base_price)

    product = await product_repository.save(product)

    return _to_dto(product)


@router.post("/{product_id}/variants", response_model=ProductVariantDTO, status_code=status.HTTP_201_CREATED)
async def add_product_variant(
    tenant_id: str,
    product_id: str,
    dto: CreateProductVariantDTO,
    product_repository: ProductRepository = Depends(get_product_repository),
) -> ProductVariantDTO:
    """Add a variant to a product."""
    product = await product_repository.get_by_id(
        ProductId.from_string(product_id)
    )

    if not product or str(product.tenant_id) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {product_id}",
        )

    variant = ProductVariant.create(
        sku=dto.sku,
        name=dto.name,
        price=Money.from_float(dto.price),
        stock=dto.stock,
        attributes=dto.attributes,
    )

    product.add_variant(variant)
    product = await product_repository.save(product)

    # Return the added variant
    added = product.get_variant(dto.sku)
    return ProductVariantDTO(
        sku=added.sku,
        name=added.name,
        price=added.price.to_float(),
        stock=added.stock,
        attributes=added.attributes,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    tenant_id: str,
    product_id: str,
    product_repository: ProductRepository = Depends(get_product_repository),
) -> None:
    """Delete product."""
    product = await product_repository.get_by_id(
        ProductId.from_string(product_id)
    )

    if not product or str(product.tenant_id) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {product_id}",
        )

    await product_repository.delete(product.id)


@router.post("/{product_id}/deactivate", response_model=ProductDTO)
async def deactivate_product(
    tenant_id: str,
    product_id: str,
    product_repository: ProductRepository = Depends(get_product_repository),
) -> ProductDTO:
    """Deactivate a product."""
    product = await product_repository.get_by_id(
        ProductId.from_string(product_id)
    )

    if not product or str(product.tenant_id) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {product_id}",
        )

    product.deactivate()
    product = await product_repository.save(product)

    return _to_dto(product)


@router.post("/{product_id}/activate", response_model=ProductDTO)
async def activate_product(
    tenant_id: str,
    product_id: str,
    product_repository: ProductRepository = Depends(get_product_repository),
) -> ProductDTO:
    """Activate a product."""
    product = await product_repository.get_by_id(
        ProductId.from_string(product_id)
    )

    if not product or str(product.tenant_id) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {product_id}",
        )

    product.activate()
    product = await product_repository.save(product)

    return _to_dto(product)


def _to_dto(product: Product) -> ProductDTO:
    """Convert product entity to DTO."""
    return ProductDTO(
        id=str(product.id),
        tenant_id=str(product.tenant_id),
        name=product.name,
        description=product.description,
        category=product.category,
        base_price=product.base_price.to_float(),
        currency=product.base_price.currency,
        is_active=product.is_active,
        variants=[
            ProductVariantDTO(
                sku=v.sku,
                name=v.name,
                price=v.price.to_float(),
                stock=v.stock,
                attributes=v.attributes,
            )
            for v in product.variants
        ],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )
