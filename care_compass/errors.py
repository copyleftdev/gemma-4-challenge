"""Shared exceptions for Care Compass."""


class CareCompassError(RuntimeError):
    """Base class for expected application errors."""


class ValidationError(CareCompassError):
    """Raised when validation, policy, or local model checks fail."""

