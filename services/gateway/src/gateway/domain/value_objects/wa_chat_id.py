"""WAChatId value object."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class WAChatId:
    """WhatsApp chat identifier (phone number or group ID)."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("WAChatId must be a non-empty string")
        # WhatsApp IDs typically end with @c.us (individual) or @g.us (group)
        if not re.match(r"^[\d-]+@(c\.us|g\.us|s\.whatsapp\.net)$", self.value):
            # Allow raw phone numbers too (will be formatted by WAHA)
            if not re.match(r"^[\d-]+$", self.value):
                raise ValueError(f"Invalid WAChatId format: {self.value}")

    @classmethod
    def from_phone(cls, phone: str) -> "WAChatId":
        """Create WAChatId from raw phone number."""
        # Remove any non-digit characters
        clean_phone = re.sub(r"[^\d]", "", phone)
        if not clean_phone:
            raise ValueError("Phone number must contain digits")
        # Format as WhatsApp ID
        return cls(f"{clean_phone}@c.us")

    @property
    def is_group(self) -> bool:
        """Check if this is a group chat."""
        return "@g.us" in self.value

    @property
    def phone_number(self) -> str:
        """Extract phone number from chat ID."""
        return self.value.split("@")[0]

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WAChatId):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)
