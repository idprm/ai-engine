"""PromptTemplate aggregate root entity."""
from dataclasses import dataclass, field


@dataclass
class PromptTemplate:
    """Prompt template aggregate root.

    Represents a reusable prompt template that can be
    combined with user input for AI processing.
    """
    _name: str
    _content: str
    _description: str | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def content(self) -> str:
        return self._content

    @property
    def description(self) -> str | None:
        return self._description

    def format(self, **kwargs) -> str:
        """Format the template with provided variables.

        Args:
            **kwargs: Variables to substitute in the template.

        Returns:
            Formatted prompt string.
        """
        return self._content.format(**kwargs)

    @classmethod
    def create(
        cls,
        name: str,
        content: str,
        description: str | None = None,
    ) -> "PromptTemplate":
        """Factory method to create a new PromptTemplate."""
        if not content or not content.strip():
            raise ValueError("Template content cannot be empty")
        return cls(
            _name=name,
            _content=content,
            _description=description,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "name": self._name,
            "content": self._content,
            "description": self._description,
        }
