"""SQLAlchemy implementation of ProductRepository."""
import logging

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from commerce_agent.domain.entities import Product, ProductVariant
from commerce_agent.domain.repositories import ProductRepository
from commerce_agent.domain.value_objects import ProductId, TenantId, Money
from commerce_agent.infrastructure.persistence.database import get_db_session
from commerce_agent.infrastructure.persistence.models import ProductModel, ProductVariantModel

logger = logging.getLogger(__name__)


class ProductRepositoryImpl(ProductRepository):
    """SQLAlchemy implementation of ProductRepository."""

    async def get_by_id(self, product_id: ProductId) -> Product | None:
        """Retrieve a product by its unique identifier."""
        async with get_db_session() as session:
            result = await session.execute(
                select(ProductModel).where(ProductModel.id == product_id.value)
            )
            model = result.scalar_one_or_none()
            if model:
                return self._to_entity(model, session)
            return None

    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[Product]:
        """List products for a tenant."""
        async with get_db_session() as session:
            query = select(ProductModel).where(ProductModel.tenant_id == tenant_id.value)

            if category:
                query = query.where(ProductModel.category == category)
            if active_only:
                query = query.where(ProductModel.is_active == True)

            result = await session.execute(query)
            models = result.scalars().all()
            return [self._to_entity(m, session) for m in models]

    async def search(
        self,
        tenant_id: TenantId,
        query: str,
        category: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
    ) -> list[Product]:
        """Search products by various criteria."""
        async with get_db_session() as session:
            stmt = select(ProductModel).where(
                ProductModel.tenant_id == tenant_id.value,
                ProductModel.is_active == True,
            )

            # Text search on name and description
            search_pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    ProductModel.name.ilike(search_pattern),
                    ProductModel.description.ilike(search_pattern),
                )
            )

            if category:
                stmt = stmt.where(ProductModel.category == category)

            if min_price is not None:
                stmt = stmt.where(ProductModel.base_price >= min_price)

            if max_price is not None:
                stmt = stmt.where(ProductModel.base_price <= max_price)

            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(m, session) for m in models]

    async def save(self, product: Product) -> Product:
        """Persist a product aggregate."""
        async with get_db_session() as session:
            existing = await session.get(ProductModel, product.id.value)

            if existing:
                existing.name = product.name
                existing.description = product.description
                existing.category = product.category
                existing.base_price = product.base_price.amount
                existing.is_active = product.is_active

                # Sync variants
                await self._sync_variants(session, existing, product.variants)
            else:
                model = self._to_model(product)
                session.add(model)

            await session.flush()
            return product

    async def _sync_variants(
        self,
        session: AsyncSession,
        product_model: ProductModel,
        variants: list[ProductVariant],
    ) -> None:
        """Sync product variants."""
        # Get existing variants
        result = await session.execute(
            select(ProductVariantModel).where(ProductVariantModel.product_id == product_model.id)
        )
        existing_variants = {v.sku: v for v in result.scalars().all()}

        # Update or create variants
        for variant in variants:
            if variant.sku in existing_variants:
                # Update existing
                existing = existing_variants[variant.sku]
                existing.name = variant.name
                existing.price = variant.price.amount
                existing.stock = variant.stock
                existing.attributes = variant.attributes
            else:
                # Create new
                new_variant = ProductVariantModel(
                    product_id=product_model.id,
                    sku=variant.sku,
                    name=variant.name,
                    price=variant.price.amount,
                    stock=variant.stock,
                    attributes=variant.attributes,
                )
                session.add(new_variant)

    async def delete(self, product_id: ProductId) -> bool:
        """Delete a product."""
        async with get_db_session() as session:
            model = await session.get(ProductModel, product_id.value)
            if model:
                await session.delete(model)
                return True
            return False

    def _to_entity(self, model: ProductModel, session: AsyncSession) -> Product:
        """Convert SQLAlchemy model to domain entity."""
        # Get variants
        variants = []
        for v in model.variants:
            variant = ProductVariant.create(
                variant_id=v.id,
                sku=v.sku,
                name=v.name,
                price=Money(amount=v.price),
                stock=v.stock,
                attributes=v.attributes,
            )
            variants.append(variant)

        product = Product.__new__(Product)
        product._id = ProductId(value=model.id)
        product._tenant_id = TenantId(value=model.tenant_id)
        product._name = model.name
        product._description = model.description or ""
        product._category = model.category
        product._base_price = Money(amount=model.base_price, currency=model.currency)
        product._is_active = model.is_active
        product._variants = variants
        product._created_at = model.created_at
        product._updated_at = model.updated_at
        product._events = []
        return product

    def _to_model(self, entity: Product) -> ProductModel:
        """Convert domain entity to SQLAlchemy model."""
        model = ProductModel(
            id=entity.id.value,
            tenant_id=entity.tenant_id.value,
            name=entity.name,
            description=entity.description,
            category=entity.category,
            base_price=entity.base_price.amount,
            is_active=entity.is_active,
        )

        # Add variants
        for variant in entity.variants:
            model.variants.append(ProductVariantModel(
                sku=variant.sku,
                name=variant.name,
                price=variant.price.amount,
                stock=variant.stock,
                attributes=variant.attributes,
            ))

        return model
