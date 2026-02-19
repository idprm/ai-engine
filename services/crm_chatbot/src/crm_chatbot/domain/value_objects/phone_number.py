"""PhoneNumber value object."""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PhoneNumber:
    """Immutable phone number value object.

    Stores phone number in E.164 format: +<country_code><number>
    Example: +6281234567890
    """

    value: str

    def __post_init__(self):
        """Validate and normalize phone number."""
        # Remove any non-digit characters except leading +
        normalized = self.value.strip()
        if not normalized.startswith("+"):
            # Assume Indonesian number if no country code
            if normalized.startswith("0"):
                normalized = "+62" + normalized[1:]
            elif normalized.startswith("62"):
                normalized = "+" + normalized
            else:
                raise ValueError(f"Invalid phone number format: {self.value}")

        # Validate format: + followed by 10-15 digits
        if not re.match(r"^\+\d{10,15}$", normalized):
            raise ValueError(f"Invalid phone number format: {self.value}")

        # Use object.__setattr__ because frozen dataclass
        object.__setattr__(self, "value", normalized)

    @classmethod
    def from_raw(cls, raw: str) -> "PhoneNumber":
        """Create PhoneNumber from raw input, handling various formats."""
        # Remove spaces, dashes, parentheses
        cleaned = re.sub(r"[\s\-\(\)]", "", raw)
        return cls(value=cleaned)

    def to_whatsapp_id(self) -> str:
        """Convert to WhatsApp ID format (without +, with @s.whatsapp.net)."""
        return f"{self.value[1:]}@s.whatsapp.net"

    def to_display(self) -> str:
        """Format for display with country code."""
        return self.value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"PhoneNumber('{self.value}')"
