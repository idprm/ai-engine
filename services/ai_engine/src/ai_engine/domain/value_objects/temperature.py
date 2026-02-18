"""Temperature value object."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Temperature:
    """LLM temperature value object for controlling randomness."""
    value: float

    def __post_init__(self):
        if not 0.0 <= self.value <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")

    @classmethod
    def deterministic(cls) -> "Temperature":
        """Create a low temperature for more deterministic outputs."""
        return cls(0.0)

    @classmethod
    def balanced(cls) -> "Temperature":
        """Create a balanced temperature (default)."""
        return cls(0.7)

    @classmethod
    def creative(cls) -> "Temperature":
        """Create a high temperature for more creative outputs."""
        return cls(1.2)

    def __float__(self) -> float:
        return self.value

    def __str__(self) -> str:
        return str(self.value)
