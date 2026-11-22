from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models import OrderStatus


class CoffeeSize(str, Enum):
    S = "S"
    M = "M"
    L = "L"


class OrderCreateRequest(BaseModel):
    shop_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    size: CoffeeSize = CoffeeSize.M
    sugar: int = Field(default=0, ge=0, le=5)
    milk: str = Field(default="regular", min_length=1, max_length=30)
    extra_shots: int = Field(default=0, ge=0, le=3)


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float


class OrderResponse(BaseModel):
    id: int
    order_id: str
    user_id: str
    shop_id: str
    shop_name: str
    status: OrderStatus
    customization: dict[str, Any] | None
    qr_payload: dict[str, str]
    qr_image: str
    items: list[OrderItemResponse]
    created_at: datetime


class OrderStatusRequest(BaseModel):
    status: OrderStatus
    qr_payload: dict[str, str] | None = None


class QRVerificationRequest(BaseModel):
    qr_payload: dict[str, str]


class OrderStatusResponse(BaseModel):
    order_id: str
    status: OrderStatus
    message: str
    qr_valid: bool | None = None
