"""LLMConfig aggregate root entity."""
from dataclasses import dataclass, field

from ai_engine.domain.value_objects import ModelName, Provider, Temperature


@dataclass
class LLMConfig:
    """LLM configuration aggregate root.

    Represents a configured LLM provider/model combination
    that can be used for processing jobs.
    """
    _name: str
    _provider: Provider
    _model_name: ModelName
    _api_key_env: str
    _temperature: Temperature = field(default_factory=Temperature.balanced)
    _max_tokens: int = 4096
    _is_active: bool = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def provider(self) -> Provider:
        return self._provider

    @property
    def model_name(self) -> ModelName:
        return self._model_name

    @property
    def api_key_env(self) -> str:
        return self._api_key_env

    @property
    def temperature(self) -> Temperature:
        return self._temperature

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def is_active(self) -> bool:
        return self._is_active

    def deactivate(self) -> None:
        """Deactivate this configuration."""
        self._is_active = False

    def activate(self) -> None:
        """Activate this configuration."""
        self._is_active = True

    def update_temperature(self, temperature: Temperature) -> None:
        """Update the temperature setting."""
        self._temperature = temperature

    def update_max_tokens(self, max_tokens: int) -> None:
        """Update the max tokens setting."""
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        self._max_tokens = max_tokens

    @classmethod
    def create(
        cls,
        name: str,
        provider: Provider,
        model_name: ModelName,
        api_key_env: str,
        temperature: Temperature | None = None,
        max_tokens: int = 4096,
    ) -> "LLMConfig":
        """Factory method to create a new LLMConfig."""
        return cls(
            _name=name,
            _provider=provider,
            _model_name=model_name,
            _api_key_env=api_key_env,
            _temperature=temperature or Temperature.balanced(),
            _max_tokens=max_tokens,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "name": self._name,
            "provider": str(self._provider),
            "model_name": str(self._model_name),
            "api_key_env": self._api_key_env,
            "temperature": float(self._temperature),
            "max_tokens": self._max_tokens,
            "is_active": self._is_active,
        }
