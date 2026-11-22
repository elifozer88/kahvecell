from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_access_token, create_refresh_token, get_current_user
from app.database import get_db
from app.models import OtpRequest, RefreshToken, User, UserRole
from app.schemas import (
    CompleteProfileRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    VerifyOtpRequest,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
OTP_CODE = "1234"


@router.post("/register", status_code=status.HTTP_200_OK)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    db.query(OtpRequest).filter(
        OtpRequest.phone_number == payload.phone_number,
        OtpRequest.is_used == False,
    ).update({"is_used": True})

    otp = OtpRequest(
        phone_number=payload.phone_number,
        code=OTP_CODE,
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    db.add(otp)
    db.commit()
    return {"message": "SMS OTP gönderildi (simülasyon)", "otp": OTP_CODE}


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    otp = db.scalar(
        select(OtpRequest)
        .where(OtpRequest.phone_number == payload.phone_number)
        .where(OtpRequest.code == payload.code)
        .where(OtpRequest.is_used == False)
        .where(OtpRequest.expires_at > datetime.utcnow())
        .order_by(OtpRequest.created_at.desc())
    )
    if otp is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP geçersiz veya süresi dolmuş")

    otp.is_used = True
    user = db.scalar(select(User).where(User.phone_number == payload.phone_number))
    if user is None:
        user = User(
            phone_number=payload.phone_number,
            full_name="",
            role=UserRole.CUSTOMER,
            is_verified=True,
            preferences=None,
        )
        db.add(user)
        db.flush()
    else:
        user.is_verified = True

    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(db, user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token == payload.refresh_token,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    if token_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token geçersiz")

    user = db.scalar(select(User).where(User.id == token_row.user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı")

    token_row.is_revoked = True
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(db, user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserResponse)
def complete_profile(payload: CompleteProfileRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.full_name = payload.full_name
    current_user.email = payload.email
    current_user.preferences = payload.preferences
    db.commit()
    db.refresh(current_user)
    return current_user
