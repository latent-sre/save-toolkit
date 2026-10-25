"""Order payload schema validation using Pydantic v2."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderSchema(BaseModel):
    """Pydantic model validating incoming JSON order payloads."""

    model_config = ConfigDict(extra="forbid")

    order_id: str
    symbol: str
    quantity: int = Field(gt=0)
    limit_price: Decimal = Field(gt=Decimal(0), decimal_places=2)
    submitted_at: datetime
    tags: list[str]

    @field_validator("submitted_at")
    @classmethod
    def validate_timezone(cls, v: datetime) -> datetime:
        """Ensure the datetime has an explicit timezone."""
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("submitted_at must have timezone information")
        return v


# Convenient aliases for callers
Order = OrderSchema
OrderPayload = OrderSchema


def validate_order(data: dict[str, Any] | str | bytes) -> OrderSchema:
    """Validate an order payload from a dictionary, JSON string, or bytes.

    Raises ValidationError if validation fails.
    """
    if isinstance(data, (str, bytes)):
        return OrderSchema.model_validate_json(data)
    return OrderSchema.model_validate(data)
