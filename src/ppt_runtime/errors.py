"""Custom exceptions for ppt_runtime."""


class PptRuntimeError(Exception):
    """Base exception for ppt_runtime."""


class TokenNotFoundError(PptRuntimeError):
    """Raised when a named token is not in the design system."""


class CanvasNotFoundError(PptRuntimeError):
    """Raised when a canvas name is not in the design system."""


class GridError(PptRuntimeError):
    """Raised on grid math violations (out-of-bounds, overflow)."""
