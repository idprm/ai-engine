"""Routes package for CRM chatbot interface."""

from crm_chatbot.interface.routes.api import api_router, create_api_router

__all__ = ["api_router", "create_api_router"]
