"""Tool package — importing this package registers the full tool registry."""

from app.tools import (
    builtin,  # noqa: F401  (registers the ten built-in tools)
    registry,  # noqa: F401
)
