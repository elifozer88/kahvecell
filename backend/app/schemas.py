from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import UserRole


class RegisterRequest(BaseModel):
    phone_number: str = Field(pattern=r"^05[0-9]{9}$")


class VerifyOtpRequest(BaseModel):
    phone_number: str = Field(pattern=r"^05[0-9]{9}$")
    code: str = Field(pattern=r"^[0-9]{4}$")


class CompleteProfileRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr | None = None
    preferences: dict | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: str
    email: EmailStr | None
    role: UserRole
    is_verified: bool
    preferences: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
