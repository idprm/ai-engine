"""WASession value object."""
from dataclasses import dataclass
from enum import Enum


class WASessionStatus(str, Enum):
    """WhatsApp session status."""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    QR = "QR"  # QR code pending scan
    FAILED = "FAILED"


@dataclass(frozen=True)
class WASession:
    """WhatsApp session information."""
    name: str
    status: WASessionStatus = WASessionStatus.DISCONNECTED

    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Session name must be a non-empty string")
        if not isinstance(self.status, WASessionStatus):
            if isinstance(self.status, str):
                try:
                    object.__setattr__(self, "status", WASessionStatus(self.status.upper()))
                except ValueError:
                    raise ValueError(f"Invalid session status: {self.status}")
            else:
                raise ValueError("Status must be a WASessionStatus or valid string")

    @property
    def is_connected(self) -> bool:
        """Check if session is connected."""
        return self.status == WASessionStatus.CONNECTED

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WASession):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(self.name)
