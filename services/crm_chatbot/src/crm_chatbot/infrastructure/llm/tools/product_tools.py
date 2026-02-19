"""Product tools for CRM agent."""
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def search_products(
    query: str,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> str:
    """Search for products in the catalog.

    Use this tool when the customer wants to browse or find products.
    Returns a list of matching products with basic information.

    Args:
        query: Search query (product name or description keywords).
        category: Optional category filter (e.g., "electronics", "clothing").
        min_price: Optional minimum price filter.
        max_price: Optional maximum price filter.

    Returns:
        JSON string with list of matching products.
    """
    import json
    # This is a placeholder - actual implementation will be injected
    # The service layer will provide the actual repository access
    return json.dumps({
        "products": [],
        "message": "Search requires tenant context - will be executed by service",
        "query": query,
    })


@tool
async def get_product_details(product_id: str) -> str:
    """Get detailed information about a specific product.

    Use this tool when the customer asks about a specific product.
    Returns full product details including variants and pricing.

    Args:
        product_id: The unique identifier of the product.

    Returns:
        JSON string with product details and variants.
    """
    import json
    return json.dumps({
        "product": None,
        "message": "Get product requires tenant context - will be executed by service",
        "product_id": product_id,
    })


@tool
async def check_stock(sku: str) -> str:
    """Check stock availability for a specific product variant.

    Use this tool when the customer wants to know if a specific
    variant is available.

    Args:
        sku: The SKU of the product variant to check.

    Returns:
        JSON string with stock information.
    """
    import json
    return json.dumps({
        "sku": sku,
        "in_stock": False,
        "quantity": 0,
        "message": "Stock check requires tenant context - will be executed by service",
    })


# Tool executor functions that will be called by the service layer
async def execute_search_products(
    product_repository,
    tenant_id: str,
    query: str,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> dict[str, Any]:
    """Execute product search with repository access."""
    from crm_chatbot.domain.value_objects import TenantId

    products = await product_repository.search(
        tenant_id=TenantId.from_string(tenant_id),
        query=query,
        category=category,
        min_price=int(min_price * 100) if min_price else None,
        max_price=int(max_price * 100) if max_price else None,
    )

    return {
        "products": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description[:200] if p.description else "",
                "category": p.category,
                "base_price": p.base_price.to_float(),
                "variants_count": len(p.variants),
            }
            for p in products[:10]  # Limit to 10 results
        ],
        "total": len(products),
    }


async def execute_get_product_details(
    product_repository,
    product_id: str,
) -> dict[str, Any]:
    """Execute get product details with repository access."""
    from crm_chatbot.domain.value_objects import ProductId

    product = await product_repository.get_by_id(
        ProductId.from_string(product_id)
    )

    if not product:
        return {"error": "Product not found", "product_id": product_id}

    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "base_price": product.base_price.to_float(),
        "variants": [
            {
                "sku": v.sku,
                "name": v.name,
                "price": v.price.to_float(),
                "stock": v.stock,
                "attributes": v.attributes,
            }
            for v in product.variants
        ],
    }


async def execute_check_stock(
    product_repository,
    tenant_id: str,
    sku: str,
) -> dict[str, Any]:
    """Execute stock check with repository access."""
    from crm_chatbot.domain.value_objects import TenantId

    # Search through products to find the SKU
    products = await product_repository.list_by_tenant(
        TenantId.from_string(tenant_id),
    )

    for product in products:
        for variant in product.variants:
            if variant.sku == sku:
                return {
                    "sku": sku,
                    "product_name": product.name,
                    "variant_name": variant.name,
                    "in_stock": variant.stock > 0,
                    "quantity": variant.stock,
                    "price": variant.price.to_float(),
                }

    return {
        "sku": sku,
        "error": "SKU not found",
    }
