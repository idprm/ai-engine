"""Response validation utilities for LLM outputs.

This module provides validation logic to ensure LLM responses are
meaningful and not empty, error messages, or other invalid content.
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseQuality(Enum):
    """Quality assessment of LLM response."""

    VALID = "valid"
    EMPTY = "empty"
    WHITESPACE_ONLY = "whitespace_only"
    TOO_SHORT = "too_short"
    ERROR_INDICATOR = "error_indicator"


@dataclass(frozen=True)
class ValidationResult:
    """Result of response validation.

    Attributes:
        is_valid: Whether the response passes validation.
        quality: The quality classification of the response.
        reason: Human-readable explanation if validation failed.
    """

    is_valid: bool
    quality: ResponseQuality
    reason: str | None = None


# Patterns that might indicate an error or incomplete response
# These are common patterns from LLMs when they can't or won't respond properly
ERROR_PATTERNS = [
    # Explicit error prefixes
    r"^error:",
    r"^\[error\]",
    r"^exception:",
    # Refusal patterns
    r"^sorry,?\s+i (can't|cannot|am unable)",
    r"^i apologize,?\s+(but\s+)?i",
    r"^i('m| am) sorry,?\s+(but\s+)?(i|unable)",
    # AI self-identification that often precedes refusals
    r"^as an ai",
    r"^as a language model",
    r"^i am (an|a) ai",
    # Incomplete response indicators
    r"^\.\.\.$",
    r"^\[truncated\]",
    r"^\[content (removed|blocked)\]",
]


def validate_response(
    response: str | None,
    min_length: int = 10,
    check_error_patterns: bool = True,
) -> ValidationResult:
    """Validate an LLM response for quality.

    Checks for common issues like empty responses, whitespace-only content,
    responses that are too short to be useful, and patterns that indicate
    the LLM is refusing or unable to respond.

    Args:
        response: The response text to validate.
        min_length: Minimum acceptable response length in characters.
        check_error_patterns: Whether to check for error indicator patterns.

    Returns:
        ValidationResult with quality assessment and reason if invalid.

    Example:
        ```python
        validation = validate_response(llm_response.content)
        if not validation.is_valid:
            logger.warning(f"Invalid response: {validation.reason}")
            # Trigger retry or fallback
        ```
    """
    # Check for None
    if response is None:
        return ValidationResult(
            is_valid=False,
            quality=ResponseQuality.EMPTY,
            reason="Response is None",
        )

    # Check for empty string
    if not response:
        return ValidationResult(
            is_valid=False,
            quality=ResponseQuality.EMPTY,
            reason="Response is empty string",
        )

    # Check for whitespace-only content
    stripped = response.strip()
    if not stripped:
        return ValidationResult(
            is_valid=False,
            quality=ResponseQuality.WHITESPACE_ONLY,
            reason="Response contains only whitespace",
        )

    # Check minimum length
    if len(stripped) < min_length:
        return ValidationResult(
            is_valid=False,
            quality=ResponseQuality.TOO_SHORT,
            reason=f"Response too short: {len(stripped)} chars (min: {min_length})",
        )

    # Check for error patterns
    if check_error_patterns:
        lower_response = stripped.lower()
        for pattern in ERROR_PATTERNS:
            if re.match(pattern, lower_response):
                return ValidationResult(
                    is_valid=False,
                    quality=ResponseQuality.ERROR_INDICATOR,
                    reason=f"Response matches error pattern: {pattern}",
                )

    # All checks passed
    return ValidationResult(
        is_valid=True,
        quality=ResponseQuality.VALID,
    )


def is_retryable_failure(validation: ValidationResult) -> bool:
    """Check if a validation failure might succeed on retry.

    Some validation failures (like error indicators) are unlikely to
    succeed on retry, while others (empty/timeout) might.

    Args:
        validation: The validation result to check.

    Returns:
        True if the failure might succeed on retry, False otherwise.
    """
    if validation.is_valid:
        return False

    # Empty and whitespace failures might be transient
    if validation.quality in (
        ResponseQuality.EMPTY,
        ResponseQuality.WHITESPACE_ONLY,
    ):
        return True

    # Too short might succeed with different parameters
    if validation.quality == ResponseQuality.TOO_SHORT:
        return True

    # Error indicators (refusals) are unlikely to change on retry
    return False
