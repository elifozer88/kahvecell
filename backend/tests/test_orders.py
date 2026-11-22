from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import (
    OrderStatus,
    Product,
    Shop,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)


@pytest.fixture
def order_client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    with TestingSession() as db:
        customer = User(
            phone_number="05550000001",
            full_name="Test Customer",
            role=UserRole.CUSTOMER,
            is_verified=True,
        )
        owner = User(
            phone_number="05550000002",
            full_name="Test Owner",
            role=UserRole.SHOP_OWNER,
            is_verified=True,
        )
        db.add_all([customer, owner])
        db.flush()
        shop = Shop(
            owner_id=owner.id,
            name="Buca Test Kahve",
            address="Buca, İzmir",
            latitude=38.3892,
            longitude=27.1305,
        )
        db.add(shop)
        db.flush()
        product = Product(shop_id=shop.id, name="Latte", base_price=90)
        subscription = Subscription(
            user_id=customer.id,
            plan_type="STARTER",
            remaining_credits=2,
            status=SubscriptionStatus.ACTIVE,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add_all([product, subscription])
        db.commit()
        customer_id, owner_id, shop_id, product_id = customer.id, owner.id, shop.id, product.id

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    with TestingSession() as db:
        customer = db.get(User, customer_id)
        owner = db.get(User, owner_id)
        customer_token = create_access_token(customer)
        owner_token = create_access_token(owner)
    client.customer_headers = {"Authorization": f"Bearer {customer_token}"}
    client.owner_headers = {"Authorization": f"Bearer {owner_token}"}
    client.shop_id = shop_id
    client.product_id = product_id
    client.testing_session = TestingSession
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_order_requires_subscription_and_decrements_credit(order_client):
    request = {
        "shop_id": order_client.shop_id,
        "product_id": order_client.product_id,
        "size": "M",
        "sugar": 1,
        "milk": "oat",
        "extra_shots": 1,
    }
    response = order_client.post("/api/v1/orders", json=request, headers=order_client.customer_headers)
    assert response.status_code == 201
    created = response.json()
    assert set(created["qr_payload"]) == {"order_id", "user_id", "shop_id", "created_at", "signature"}
    assert created["qr_image"].startswith("data:image/png;base64,")

    with order_client.testing_session() as db:
        subscription = db.scalar(select(Subscription))
        assert subscription.remaining_credits == 1


def test_owner_tracks_order_and_qr_completes_delivery(order_client):
    request = {"shop_id": order_client.shop_id, "product_id": order_client.product_id}
    created = order_client.post("/api/v1/orders", json=request, headers=order_client.customer_headers).json()
    order_id = created["id"]

    incoming = order_client.get("/api/v1/orders/shop-owner/incoming", headers=order_client.owner_headers)
    assert incoming.status_code == 200
    assert incoming.json()[0]["id"] == order_id

    for next_status in ("ACCEPTED", "PREPARING", "READY"):
        result = order_client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": next_status},
            headers=order_client.owner_headers,
        )
        assert result.status_code == 200

    invalid_payload = {**created["qr_payload"], "signature": "invalid"}
    invalid_result = order_client.post(
        f"/api/v1/orders/{order_id}/verify-qr",
        json={"qr_payload": invalid_payload},
        headers=order_client.owner_headers,
    )
    assert invalid_result.status_code == 400

    completed = order_client.post(
        f"/api/v1/orders/{order_id}/verify-qr",
        json={"qr_payload": created["qr_payload"]},
        headers=order_client.owner_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == OrderStatus.COMPLETED.value
    assert completed.json()["qr_valid"] is True


def test_order_rejected_without_active_subscription_or_credits(order_client):
    request = {"shop_id": order_client.shop_id, "product_id": order_client.product_id}
    with order_client.testing_session() as db:
        subscription = db.scalar(select(Subscription))
        subscription.remaining_credits = 0
        db.commit()

    response = order_client.post("/api/v1/orders", json=request, headers=order_client.customer_headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "NO_COFFEE_CREDITS"


def test_order_rejected_without_active_subscription(order_client):
    with order_client.testing_session() as db:
        subscription = db.scalar(select(Subscription))
        subscription.status = SubscriptionStatus.CANCELLED
        db.commit()

    response = order_client.post(
        "/api/v1/orders",
        json={"shop_id": order_client.shop_id, "product_id": order_client.product_id},
        headers=order_client.customer_headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ACTIVE_SUBSCRIPTION_REQUIRED"


def test_unlimited_subscription_does_not_decrement_credit(order_client):
    with order_client.testing_session() as db:
        subscription = db.scalar(select(Subscription))
        subscription.plan_type = "UNLIMITED"
        subscription.remaining_credits = -1
        db.commit()

    response = order_client.post(
        "/api/v1/orders",
        json={"shop_id": order_client.shop_id, "product_id": order_client.product_id},
        headers=order_client.customer_headers,
    )
    assert response.status_code == 201
    with order_client.testing_session() as db:
        subscription = db.scalar(select(Subscription))
        assert subscription.remaining_credits == -1
