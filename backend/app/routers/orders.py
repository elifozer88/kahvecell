import base64
import hashlib
import hmac
import json
import os
from datetime import datetime
from io import BytesIO
from typing import Any

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Order,
    OrderItem,
    OrderStatus,
    Product,
    Shop,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)
from app.schemas_orders import (
    OrderCreateRequest,
    OrderItemResponse,
    OrderResponse,
    OrderStatusRequest,
    OrderStatusResponse,
    QRVerificationRequest,
)

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])
QR_SECRET = os.getenv("KAHVECELL_QR_SECRET", "kahvecell-dev-qr-secret-change-before-production").encode("utf-8")
QR_FIELDS = {"order_id", "user_id", "shop_id", "created_at", "signature"}
OWNER_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING},
    OrderStatus.PREPARING: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.COMPLETED},
}


def canonical_json(payload: dict[str, str]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def create_signed_qr(order: Order, user: User, shop: Shop) -> dict[str, str]:
    payload = {
        "order_id": order.public_id,
        "user_id": user.public_id,
        "shop_id": shop.public_id,
        "created_at": order.created_at.isoformat(timespec="seconds") + "Z",
    }
    payload["signature"] = hmac.new(
        QR_SECRET,
        canonical_json(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return payload


def is_valid_qr_payload(payload: dict[str, Any], order: Order) -> bool:
    if set(payload) != QR_FIELDS or any(not isinstance(value, str) for value in payload.values()):
        return False
    signature = payload.get("signature", "")
    unsigned_payload = {key: value for key, value in payload.items() if key != "signature"}
    expected_signature = hmac.new(
        QR_SECRET,
        canonical_json(unsigned_payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return False

    try:
        stored_payload = json.loads(order.qr_code)
    except (TypeError, json.JSONDecodeError):
        return False
    return hmac.compare_digest(canonical_json(payload), canonical_json(stored_payload))


def qr_image_data(payload: dict[str, str]) -> str:
    image = qrcode.make(canonical_json(payload))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def serialize_order(order: Order) -> OrderResponse:
    payload = json.loads(order.qr_code)
    return OrderResponse(
        id=order.id,
        order_id=order.public_id,
        user_id=order.user.public_id,
        shop_id=order.shop.public_id,
        shop_name=order.shop.name,
        status=order.status,
        customization=order.customization,
        qr_payload=payload,
        qr_image=qr_image_data(payload),
        items=[
            OrderItemResponse(
                product_id=item.product_id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in order.items
        ],
        created_at=order.created_at,
    )


def load_order(db: Session, order_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.shop),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
        .where(Order.id == order_id)
    )


def can_manage_shop_order(user: User, order: Order) -> bool:
    return user.role == UserRole.ADMIN or (
        user.role == UserRole.SHOP_OWNER and order.shop.owner_id == user.id
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Yalnızca müşteri hesabı sipariş verebilir")

    subscription = db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at > datetime.utcnow(),
        )
        .order_by(Subscription.started_at.desc())
    )
    if subscription is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "ACTIVE_SUBSCRIPTION_REQUIRED", "message": "Sipariş vermek için aktif bir aboneliğiniz olmalı."},
        )
    if subscription.remaining_credits == 0:
        raise HTTPException(
            status_code=403,
            detail={"code": "NO_COFFEE_CREDITS", "message": "Kahve hakkınız kalmamış. Paketinizi yenileyin veya yükseltin."},
        )

    shop = db.scalar(select(Shop).where(Shop.id == payload.shop_id))
    if shop is None:
        raise HTTPException(status_code=404, detail="Dükkân bulunamadı")
    product = db.scalar(
        select(Product).where(
            Product.id == payload.product_id,
            Product.shop_id == shop.id,
            Product.is_available.is_(True),
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Bu dükkânda satılabilir ürün bulunamadı")

    order = Order(
        user_id=current_user.id,
        shop_id=shop.id,
        subscription_id=subscription.id,
        status=OrderStatus.PENDING,
        qr_code="pending",
        customization={
            "size": payload.size.value,
            "sugar": payload.sugar,
            "milk": payload.milk,
            "extra_shots": payload.extra_shots,
        },
    )
    db.add(order)
    db.flush()
    order.qr_code = json.dumps(create_signed_qr(order, current_user, shop), ensure_ascii=False)
    db.add(OrderItem(order_id=order.id, product_id=product.id, quantity=1, unit_price=product.base_price))

    if subscription.remaining_credits > 0:
        subscription.remaining_credits -= 1
    db.commit()
    saved_order = load_order(db, order.id)
    return serialize_order(saved_order)


@router.get("/history", response_model=list[OrderResponse])
def customer_order_history(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orders = db.scalars(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.shop),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    ).all()
    return [serialize_order(order) for order in orders]


@router.get("/shop-owner/incoming", response_model=list[OrderResponse])
def shop_owner_incoming_orders(
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.SHOP_OWNER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Yalnızca dükkân sahibi siparişlerini görebilir")

    statement = (
        select(Order)
        .join(Shop, Order.shop_id == Shop.id)
        .options(
            selectinload(Order.user),
            selectinload(Order.shop),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
        .order_by(Order.created_at.desc())
    )
    if current_user.role == UserRole.SHOP_OWNER:
        statement = statement.where(Shop.owner_id == current_user.id)
    if order_status is not None:
        statement = statement.where(Order.status == order_status)
    orders = db.scalars(statement).all()
    return [serialize_order(order) for order in orders]


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = load_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı")
    if order.user_id != current_user.id and not can_manage_shop_order(current_user, order):
        raise HTTPException(status_code=403, detail="Bu siparişi görüntüleme yetkiniz yok")
    return serialize_order(order)


@router.patch("/{order_id}/status", response_model=OrderStatusResponse)
def update_order_status(
    order_id: int,
    payload: OrderStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = load_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı")
    if not can_manage_shop_order(current_user, order):
        raise HTTPException(status_code=403, detail="Yalnızca siparişin bağlı olduğu dükkân sahibi durumu değiştirebilir")
    if payload.status not in OWNER_TRANSITIONS.get(order.status, set()):
        raise HTTPException(status_code=409, detail=f"Geçersiz durum geçişi: {order.status.value} -> {payload.status.value}")

    if payload.status == OrderStatus.COMPLETED:
        if payload.qr_payload is None or not is_valid_qr_payload(payload.qr_payload, order):
            raise HTTPException(status_code=400, detail="QR kod geçersiz veya siparişle eşleşmiyor; teslim işaretlenmedi")

    order.status = payload.status
    db.commit()
    return OrderStatusResponse(
        order_id=order.public_id,
        status=order.status,
        message="QR doğrulandı, sipariş teslim edildi" if order.status == OrderStatus.COMPLETED else "Sipariş durumu güncellendi",
        qr_valid=True if order.status == OrderStatus.COMPLETED else None,
    )


@router.post("/{order_id}/verify-qr", response_model=OrderStatusResponse)
def verify_order_qr(
    order_id: int,
    payload: QRVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = load_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı")
    if not can_manage_shop_order(current_user, order):
        raise HTTPException(status_code=403, detail="Yalnızca siparişin bağlı olduğu dükkân doğrulama yapabilir")
    if not is_valid_qr_payload(payload.qr_payload, order):
        raise HTTPException(status_code=400, detail="QR imzası geçersiz veya bu siparişe ait değil")
    if order.status != OrderStatus.READY:
        raise HTTPException(status_code=409, detail="Teslim için sipariş önce HAZIR durumunda olmalı")

    order.status = OrderStatus.COMPLETED
    db.commit()
    return OrderStatusResponse(
        order_id=order.public_id,
        status=order.status,
        message="QR imzası doğrulandı; sipariş teslim edildi",
        qr_valid=True,
    )
