"""Runtime credential configuration for recovery utilities."""

from __future__ import annotations

import os

KERNEL_API_KEY_ENV = "RAE_KERNEL_API_KEY"


def require_kernel_api_key(explicit: str | None = None) -> str:
    """Return an injected/provider key or fail before any protected work starts."""
    value = explicit if explicit is not None else os.environ.get(KERNEL_API_KEY_ENV)
    if not value or not value.strip():
        raise RuntimeError(
            f"{KERNEL_API_KEY_ENV} is required; configure it through the runtime "
            "environment or inject it explicitly"
        )
    return value
