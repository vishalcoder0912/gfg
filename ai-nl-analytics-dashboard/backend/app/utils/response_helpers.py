"""
Lightweight helpers for consistent responses.
"""

from __future__ import annotations

from typing import Any, Dict


def error_message(message: str, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"error": message}
    if extra:
        payload.update(extra)
    return payload

