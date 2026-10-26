"""Order payload validation schema."""

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
    """Validated order payload data structure."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    symbol: str
    quantity: StrictInt = Field(gt=0)
    limit_price: Decimal = Field(gt=0, decimal_places=2)
    submitted_at: AwareDatetime
    tags: list[str]

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("order_id must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("order_id cannot be empty or whitespace-only")
        return stripped

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("symbol must be a string")
        if not v or not v.isascii() or not v.isupper():
            raise ValueError("symbol must be non-empty uppercase ASCII")
        return v

    @field_validator("limit_price", mode="before")
    @classmethod
    def reject_float_limit_price(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("limit_price must not be a binary float")
        return v

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item) from None

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)


def validate_order_payload(payload: dict[str, object]) -> OrderPayload:
    """Validate incoming order payload against schema rules.

    Raises:
        TypeError: If payload is not a dict.
        pydantic.ValidationError: If payload violates schema constraints.
    """
    if not isinstance(payload, dict):
        raise TypeError(f"payload must be a dict, got {type(payload).__name__}")
    return OrderPayload.model_validate(payload)
