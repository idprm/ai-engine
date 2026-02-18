"""Custom exceptions for domain-driven design."""


class DomainException(Exception):
    """Base exception for all domain-related errors."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code or "DOMAIN_ERROR"
        super().__init__(self.message)


class NotFoundException(DomainException):
    """Raised when an entity or aggregate is not found."""

    def __init__(self, entity_type: str, identifier: str):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(
            message=f"{entity_type} with identifier '{identifier}' not found",
            code="NOT_FOUND"
        )


class ValidationException(DomainException):
    """Raised when domain validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message=message, code="VALIDATION_ERROR")


class ConflictException(DomainException):
    """Raised when there's a conflict with current state."""

    def __init__(self, message: str):
        super().__init__(message=message, code="CONFLICT")


class InfrastructureException(Exception):
    """Base exception for infrastructure-related errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
