"""Explicit storage policies shared by WP-08 configuration and runtime."""

from typing import Literal

MONITORED_STORAGE_INTERVAL = 5.0


def validate_storage_mode(*, quota: object, mode: object = "quota") -> Literal["quota", "monitored"]:
    """Require literal, consistent opt-in before relaxing hard quota enforcement."""
    if type(mode) is str:
        if quota is True and mode == "quota":
            return "quota"
        if quota is False and mode == "monitored":
            return "monitored"
    raise ValueError("invalid storage mode or quota combination")
