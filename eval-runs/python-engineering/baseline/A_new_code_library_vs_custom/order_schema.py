"""Order payload validation module using Pydantic."""

from __future__ import annotations

import string
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
)


class OrderPayload(BaseModel):
    """Validated representation of an incoming order payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    order_id: str
    symbol: str
    quantity: StrictInt = Field(gt=0)
    limit_price: Decimal = Field(gt=Decimal(0), decimal_places=2)
    submitted_at: AwareDatetime
    tags: list[str]

    @field_validator("order_id")
    @classmethod
    def _validate_order_id(cls, v: str) -> str:
        if not isinstance(v, str):
            raise TypeError("order_id must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("order_id must be non-empty after stripping whitespace")
        return stripped

    @field_validator("symbol")
    @classmethod
    def _validate_symbol(cls, v: str) -> str:
        if not isinstance(v, str):
            raise TypeError("symbol must be a string")
        if not v:
            raise ValueError("symbol must not be empty")
        if not all(c in string.ascii_uppercase for c in v):
            raise ValueError("symbol must consist solely of uppercase ASCII characters")
        return v

    @field_validator("quantity", mode="before")
    @classmethod
    def _reject_bool_quantity(cls, v: object) -> object:
        if isinstance(v, bool):
            raise TypeError("quantity must be an integer, not a boolean")
        if not isinstance(v, int):
            raise TypeError("quantity must be an integer")
        return v

    @field_validator("limit_price", mode="before")
    @classmethod
    def _reject_binary_float_limit_price(cls, v: object) -> object:
        if isinstance(v, bool):
            raise TypeError("limit_price cannot be a boolean")
        if isinstance(v, float):
            raise TypeError("binary float inputs are rejected for limit_price")
        return v

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item) from None

    def __contains__(self, item: object) -> bool:
        return item in type(self).model_fields

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default) if item in type(self).model_fields else default

    def keys(self):
        return type(self).model_fields.keys()

    def values(self):
        return [getattr(self, k) for k in type(self).model_fields]

    def items(self):
        return [(k, getattr(self, k)) for k in type(self).model_fields]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, dict):
            return self.model_dump() == other
        return super().__eq__(other)


# Register OrderPayload as a virtual subclass of Mapping for mapping checks
Mapping.register(OrderPayload)

Order = OrderPayload


def validate_order_payload(payload: dict[str, object]) -> OrderPayload:
    """Validate incoming order payload dictionary.

    Args:
        payload: Dictionary containing order attributes.

    Returns:
        OrderPayload: Validated and immutable order payload instance.

    Raises:
        TypeError: If payload is not a dict.
        ValueError: If validation fails.
    """
    if not isinstance(payload, dict):
        raise TypeError(f"Payload must be a dict, got {type(payload).__name__}")
    return OrderPayload.model_validate(payload)
