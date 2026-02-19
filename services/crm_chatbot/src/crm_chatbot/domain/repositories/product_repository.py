"""Product repository interface."""
from abc import ABC, abstractmethod

from crm_chatbot.domain.entities import Product
from crm_chatbot.domain.value_objects import ProductId, TenantId


class ProductRepository(ABC):
    """Abstract repository interface for Product aggregate."""

    @abstractmethod
    async def get_by_id(self, product_id: ProductId) -> Product | None:
        """Retrieve a product by its unique identifier.

        Args:
            product_id: The unique identifier of the product.

        Returns:
            The Product aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[Product]:
        """List products for a tenant.

        Args:
            tenant_id: The tenant to list products for.
            category: Optional category filter.
            active_only: Whether to include only active products.

        Returns:
            List of Product aggregates.
        """
        pass

    @abstractmethod
    async def search(
        self,
        tenant_id: TenantId,
        query: str,
        category: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
    ) -> list[Product]:
        """Search products by various criteria.

        Args:
            tenant_id: The tenant to search in.
            query: Search query for name/description.
            category: Optional category filter.
            min_price: Minimum price in smallest currency unit.
            max_price: Maximum price in smallest currency unit.

        Returns:
            List of matching Product aggregates.
        """
        pass

    @abstractmethod
    async def save(self, product: Product) -> Product:
        """Persist a product aggregate.

        Args:
            product: The product to persist.

        Returns:
            The persisted product.
        """
        pass

    @abstractmethod
    async def delete(self, product_id: ProductId) -> bool:
        """Delete a product.

        Args:
            product_id: The unique identifier of the product to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass
