"""Money value object for handling currency and amounts."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    """Immutable money value object with currency support.

    Amount is stored as the smallest currency unit (e.g., cents for USD, sen for IDR)
    to avoid floating point precision issues.
    """

    amount: int  # Amount in smallest currency unit (cents/sen)
    currency: str = "IDR"

    def __post_init__(self):
        """Validate money values."""
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("Currency must be a valid 3-letter ISO code")

    @classmethod
    def from_decimal(cls, amount: Decimal, currency: str = "IDR") -> "Money":
        """Create Money from decimal amount (in major currency unit)."""
        # Convert to smallest unit (multiply by 100 for most currencies)
        smallest_unit = int(amount * 100)
        return cls(amount=smallest_unit, currency=currency)

    @classmethod
    def from_float(cls, amount: float, currency: str = "IDR") -> "Money":
        """Create Money from float amount (in major currency unit)."""
        return cls.from_decimal(Decimal(str(amount)), currency)

    @classmethod
    def from_major_unit(cls, amount: int, currency: str = "IDR") -> "Money":
        """Create Money from major currency unit (e.g., dollars, rupiah)."""
        return cls(amount=amount * 100, currency=currency)

    def to_decimal(self) -> Decimal:
        """Convert to decimal in major currency unit."""
        return Decimal(self.amount) / Decimal(100)

    def to_float(self) -> float:
        """Convert to float in major currency unit."""
        return self.amount / 100.0

    def to_major_unit(self) -> int:
        """Get amount in major currency unit."""
        return self.amount // 100

    def __add__(self, other: "Money") -> "Money":
        """Add two money values."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract two money values."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        if self.amount < other.amount:
            raise ValueError("Result cannot be negative")
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, multiplier: int) -> "Money":
        """Multiply money by an integer."""
        if multiplier < 0:
            raise ValueError("Multiplier cannot be negative")
        return Money(amount=self.amount * multiplier, currency=self.currency)

    def __str__(self) -> str:
        """Format as human-readable string."""
        major = self.to_float()
        return f"{currency_symbol(self.currency)}{major:,.2f}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency='{self.currency}')"


def currency_symbol(currency: str) -> str:
    """Get currency symbol for a currency code."""
    symbols = {
        "IDR": "Rp",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "SGD": "S$",
        "MYR": "RM",
    }
    return symbols.get(currency, currency + " ")
