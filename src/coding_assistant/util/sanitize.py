"""Sanitize values before PostgreSQL JSON/text persistence."""

from __future__ import annotations

from typing import Any


def sanitize_for_storage(value: Any) -> Any:
    """Remove null bytes and other characters PostgreSQL text/jsonb reject."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {k: sanitize_for_storage(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_for_storage(v) for v in value]
    return value
