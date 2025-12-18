"""
Context management for session-specific WebSocket access in tools.

This module provides a context variable that allows tools to access
the current session's WebSocket connection for sending UI updates.
"""
import contextvars
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from session_handler import ClientSessionHandler

# Context variable to hold the active session handler
session_context: contextvars.ContextVar[Optional["ClientSessionHandler"]] = contextvars.ContextVar(
    "session_context", default=None
)


def get_session_handler() -> Optional["ClientSessionHandler"]:
    """
    Retrieves the current session handler from the context.

    Returns:
        The current ClientSessionHandler instance, or None if not set.
    """
    return session_context.get()


def set_session_handler(handler: "ClientSessionHandler") -> None:
    """
    Sets the current session handler in the context.

    Args:
        handler: The ClientSessionHandler instance to set.
    """
    session_context.set(handler)


def clear_session_handler() -> None:
    """
    Clears the current session handler from the context.
    """
    session_context.set(None)
