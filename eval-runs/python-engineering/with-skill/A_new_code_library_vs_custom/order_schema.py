"""Order payload validation schema using Pydantic v2."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt

__all__ = ["Order", "validate_order"]


class Order(BaseModel):
    """Validated order model.

    Rejects extra fields, non-positive quantities, non-positive or overly precise
    limit prices, and naive datetimes.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    order_id: str = Field(min_length=1, description="Unique identifier for the order")
    symbol: str = Field(min_length=1, description="Ticker symbol")
    quantity: StrictInt = Field(
        gt=0, description="Order quantity, strictly positive integer"
    )
    limit_price: Decimal = Field(
        gt=Decimal(0),
        decimal_places=2,
        description="Limit price, strictly positive with max 2 decimal places",
    )
    submitted_at: AwareDatetime = Field(
        description="Submission timestamp, must include timezone info",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="List of tag strings associated with the order",
    )


def validate_order(payload: str | bytes | dict[str, Any]) -> Order:
    """Validate incoming JSON order payload.

    Args:
        payload: JSON-encoded string, UTF-8 bytes, or pre-parsed dictionary.

    Returns:
        Validated immutable Order instance.

    Raises:
        pydantic.ValidationError: If payload fails validation constraints.
    """
    if isinstance(payload, (str, bytes)):
        return Order.model_validate_json(payload)
    return Order.model_validate(payload)
