"""Domain repository interfaces."""
from llm_worker.domain.repositories.llm_config_repository import LLMConfigRepository
from llm_worker.domain.repositories.prompt_template_repository import PromptTemplateRepository

__all__ = ["LLMConfigRepository", "PromptTemplateRepository"]
