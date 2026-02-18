"""Provider value object."""
from dataclasses import dataclass
from enum import Enum


class ProviderType(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass(frozen=True)
class Provider:
    """LLM provider value object."""
    type: ProviderType

    def __post_init__(self):
        if isinstance(self.type, str):
            object.__setattr__(self, "type", ProviderType(self.type.lower()))

    @classmethod
    def openai(cls) -> "Provider":
        return cls(ProviderType.OPENAI)

    @classmethod
    def anthropic(cls) -> "Provider":
        return cls(ProviderType.ANTHROPIC)

    @property
    def is_openai(self) -> bool:
        return self.type == ProviderType.OPENAI

    @property
    def is_anthropic(self) -> bool:
        return self.type == ProviderType.ANTHROPIC

    def __str__(self) -> str:
        return self.type.value
