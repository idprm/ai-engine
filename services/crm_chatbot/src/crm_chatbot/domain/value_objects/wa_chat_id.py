"""WAChatId value object for WhatsApp chat identifiers."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class WAChatId:
    """Immutable WhatsApp chat ID value object.

    WhatsApp chat IDs can be:
    - Individual: <phone>@s.whatsapp.net
    - Group: <group_id>@g.us
    """

    value: str

    def __post_init__(self):
        """Validate WhatsApp chat ID format."""
        if not self.value:
            raise ValueError("WAChatId cannot be empty")

        # Valid formats:
        # - <digits>@s.whatsapp.net (individual)
        # - <id>@g.us (group)
        if not re.match(r"^[\d\-]+@(s\.whatsapp\.net|g\.us)$", self.value):
            raise ValueError(f"Invalid WhatsApp chat ID format: {self.value}")

    @classmethod
    def from_phone(cls, phone: str) -> "WAChatId":
        """Create WAChatId from phone number string.

        Args:
            phone: Phone number with or without + prefix
        """
        # Clean phone number
        cleaned = phone.strip().lstrip("+")
        return cls(value=f"{cleaned}@s.whatsapp.net")

    @classmethod
    def from_group_id(cls, group_id: str) -> "WAChatId":
        """Create WAChatId from group ID."""
        return cls(value=f"{group_id}@g.us")

    @property
    def is_group(self) -> bool:
        """Check if this is a group chat."""
        return self.value.endswith("@g.us")

    @property
    def is_individual(self) -> bool:
        """Check if this is an individual chat."""
        return self.value.endswith("@s.whatsapp.net")

    def get_phone_number(self) -> str | None:
        """Extract phone number if individual chat, else None."""
        if self.is_individual:
            return self.value.split("@")[0]
        return None

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"WAChatId('{self.value}')"
