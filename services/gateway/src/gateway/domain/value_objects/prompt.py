"""Prompt value object."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Prompt:
    """User prompt for AI processing."""
    content: str

    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValueError("Prompt content cannot be empty")
        if len(self.content) > 100000:  # Reasonable limit
            raise ValueError("Prompt content exceeds maximum length of 100000 characters")

    @property
    def is_valid(self) -> bool:
        """Check if prompt is valid."""
        return bool(self.content and self.content.strip())

    def __str__(self) -> str:
        return self.content
