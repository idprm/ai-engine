"""ModelName value object."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelName:
    """LLM model name value object."""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Model name cannot be empty")
        # Normalize
        object.__setattr__(self, "value", self.value.strip())

    @classmethod
    def gpt4_turbo(cls) -> "ModelName":
        return cls("gpt-4-turbo-preview")

    @classmethod
    def gpt35_turbo(cls) -> "ModelName":
        return cls("gpt-3.5-turbo")

    @classmethod
    def claude_opus(cls) -> "ModelName":
        return cls("claude-3-opus-20240229")

    @classmethod
    def claude_sonnet(cls) -> "ModelName":
        return cls("claude-3-sonnet-20240229")

    def __str__(self) -> str:
        return self.value
