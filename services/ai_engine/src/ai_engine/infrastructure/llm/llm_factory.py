"""LLM Factory for creating LangChain model instances."""
import logging
import os
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ai_engine.domain.entities import LLMConfig

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM instances from domain configuration.

    Creates appropriate LangChain chat model instances based on
    the provider specified in the LLMConfig.
    """

    @staticmethod
    def create(config: LLMConfig) -> BaseChatModel:
        """Create a LangChain chat model from domain configuration.

        Args:
            config: The LLM configuration entity.

        Returns:
            A configured LangChain chat model instance.

        Raises:
            ValueError: If the provider is unsupported or API key is missing.
        """
        api_key = os.getenv(config.api_key_env)

        if not api_key:
            raise ValueError(
                f"API key not found for environment variable: {config.api_key_env}"
            )

        provider = str(config.provider).lower()
        model_name = str(config.model_name)
        temperature = float(config.temperature)
        max_tokens = config.max_tokens

        if provider == "openai":
            logger.debug(f"Creating OpenAI model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        elif provider == "anthropic":
            logger.debug(f"Creating Anthropic model: {model_name}")
            return ChatAnthropic(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def create_from_dict(config_dict: dict[str, Any]) -> BaseChatModel:
        """Create a LangChain chat model from a dictionary.

        Args:
            config_dict: Dictionary with provider, model_name, temperature, etc.

        Returns:
            A configured LangChain chat model instance.
        """
        api_key_env = config_dict.get("api_key_env", "")
        api_key = os.getenv(api_key_env)

        if not api_key:
            raise ValueError(
                f"API key not found for environment variable: {api_key_env}"
            )

        provider = config_dict.get("provider", "").lower()
        model_name = config_dict.get("model_name", "")
        temperature = config_dict.get("temperature", 0.7)
        max_tokens = config_dict.get("max_tokens", 4096)

        if provider == "openai":
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        elif provider == "anthropic":
            return ChatAnthropic(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
