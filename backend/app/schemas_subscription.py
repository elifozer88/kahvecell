from datetime import datetime

from pydantic import BaseModel, Field


class CardRequest(BaseModel):
    card_holder: str = Field(min_length=2, max_length=100)
    card_number: str = Field(pattern=r"^[0-9]{16}$")
    expiry_month: int = Field(ge=1, le=12)
    expiry_year: int = Field(ge=2026, le=2099)
    cvv: str = Field(pattern=r"^[0-9]{3}$")


class SubscribeRequest(BaseModel):
    plan_type: str = Field(pattern=r"^(STARTER|PREMIUM|UNLIMITED)$")
    card: CardRequest


class ChangePlanRequest(BaseModel):
    plan_type: str = Field(pattern=r"^(STARTER|PREMIUM|UNLIMITED)$")
    card: CardRequest


class PlanResponse(BaseModel):
    plan_type: str
    name: str
    price: float
    credits: int
    guest_credits: int
    priority: bool


class SubscriptionResponse(BaseModel):
    id: int
    plan_type: str
    remaining_credits: int
    status: str
    started_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    status: str
    message: str
    amount: float
    card_last_four: str
