from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Payment, PaymentStatus, Subscription, SubscriptionStatus, User
from app.schemas_subscription import ChangePlanRequest, PaymentResponse, PlanResponse, SubscribeRequest, SubscriptionResponse
from app.subscription_data import PLAN_RANK, SUBSCRIPTION_PLANS

router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


def current_active_subscription(db: Session, user_id: int) -> Subscription | None:
    return db.scalar(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        ).order_by(Subscription.started_at.desc())
    )


def process_payment(db: Session, user: User, plan_type: str, card_number: str) -> Payment:
    plan = SUBSCRIPTION_PLANS[plan_type]
    last_four = card_number[-4:]
    payment_status = PaymentStatus.SUCCESS if last_four == "4242" else PaymentStatus.FAILED
    payment = Payment(
        user_id=user.id,
        plan_type=plan_type,
        amount=plan["price"],
        status=payment_status,
        card_last_four=last_four,
    )
    db.add(payment)
    db.flush()
    return payment


@router.get("/plans", response_model=list[PlanResponse])
def list_plans():
    return [
        {"plan_type": plan_type, **plan}
        for plan_type, plan in SUBSCRIPTION_PLANS.items()
    ]


@router.get("/me", response_model=SubscriptionResponse | None)
def get_active_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return current_active_subscription(db, current_user.id)


@router.post("", response_model=PaymentResponse)
def subscribe(
    payload: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = current_active_subscription(db, current_user.id)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Zaten aktif bir aboneliğiniz var")

    payment = process_payment(db, current_user, payload.plan_type, payload.card.card_number)
    if payment.status == PaymentStatus.FAILED:
        db.commit()
        return PaymentResponse(
            status="FAILED",
            message="Ödeme reddedildi (test kartı: 4242 ile başarılı olur)",
            amount=payment.amount,
            card_last_four=payment.card_last_four,
        )

    plan = SUBSCRIPTION_PLANS[payload.plan_type]
    subscription = Subscription(
        user_id=current_user.id,
        plan_type=payload.plan_type,
        remaining_credits=plan["credits"],
        status=SubscriptionStatus.ACTIVE,
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(subscription)
    db.flush()
    payment.subscription_id = subscription.id
    db.commit()

    return PaymentResponse(
        status="SUCCESS",
        message="Abonelik aktif edildi",
        amount=payment.amount,
        card_last_four=payment.card_last_four,
    )


@router.patch("/me", response_model=PaymentResponse)
def change_plan(
    payload: ChangePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = current_active_subscription(db, current_user.id)
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aktif abonelik bulunamadı")

    if subscription.plan_type == payload.plan_type:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Zaten bu pakete ait aboneliğiniz var")

    payment = process_payment(db, current_user, payload.plan_type, payload.card.card_number)
    if payment.status == PaymentStatus.FAILED:
        db.commit()
        return PaymentResponse(
            status="FAILED",
            message="Paket değişikliği için ödeme reddedildi",
            amount=payment.amount,
            card_last_four=payment.card_last_four,
        )

    plan = SUBSCRIPTION_PLANS[payload.plan_type]
    old_rank = PLAN_RANK[subscription.plan_type]
    new_rank = PLAN_RANK[payload.plan_type]
    subscription.plan_type = payload.plan_type
    subscription.remaining_credits = plan["credits"]

    if new_rank < old_rank:
        action = "Paket düşürüldü"
    else:
        action = "Paket yükseltildi"

    payment.subscription_id = subscription.id
    db.commit()
    return PaymentResponse(
        status="SUCCESS",
        message=action,
        amount=payment.amount,
        card_last_four=payment.card_last_four,
    )


@router.post("/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = current_active_subscription(db, current_user.id)
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aktif abonelik bulunamadı")

    subscription.status = SubscriptionStatus.CANCELLED
    db.commit()
    db.refresh(subscription)
    return subscription
