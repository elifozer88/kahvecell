from datetime import datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.migrations import ensure_current_schema
from app.models import (
    Product,
    Shop,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)

ensure_current_schema()
Base.metadata.create_all(bind=engine)
password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

SHOPS = [
    {
        "name": "Alsancak Kahve Atölyesi",
        "address": "Kıbrıs Şehitleri Cd., Alsancak, Konak/İzmir",
        "latitude": 38.4366,
        "longitude": 27.1436,
        "opening_hours": "08:00-23:00",
        "is_open": True,
    },
    {
        "name": "Konak Tarihi Kahvecisi",
        "address": "Anafartalar Cd., Konak/İzmir",
        "latitude": 38.4189,
        "longitude": 27.1287,
        "opening_hours": "07:30-22:30",
        "is_open": True,
    },
    {
        "name": "Karşıyaka Sahil Kahve",
        "address": "Sakarya Cd., Bostanlı, Karşıyaka/İzmir",
        "latitude": 38.4560,
        "longitude": 27.0892,
        "opening_hours": "08:00-23:30",
        "is_open": True,
    },
    {
        "name": "Bornova Kampüs Kahvesi",
        "address": "Kazımdirik Mah., Bornova/İzmir",
        "latitude": 38.4624,
        "longitude": 27.2092,
        "opening_hours": "08:30-23:00",
        "is_open": True,
    },
    {
        "name": "Buca Yeşil Kahve",
        "address": "İsmetpaşa Mah., Buca/İzmir",
        "latitude": 38.3892,
        "longitude": 27.1305,
        "opening_hours": "09:00-22:00",
        "is_open": True,
    },
]

PRODUCTS = [
    ("Espresso", "Yoğun ve kısa kahve", 55.0),
    ("Americano", "Espresso ve sıcak su", 65.0),
    ("Cappuccino", "Espresso, süt ve süt köpüğü", 85.0),
    ("Latte", "Sütlü ve yumuşak espresso", 90.0),
    ("Türk Kahvesi", "Geleneksel fincan kahvesi", 75.0),
]


def run_seed():
    ensure_current_schema()
    db = SessionLocal()
    try:
        test_user = db.scalar(select(User).where(User.phone_number == "05551112233"))
        if test_user is None:
            test_user = User(
                phone_number="05551112233",
                full_name="İzmir Kahve Test Kullanıcısı",
                email="test@example.com",
                password_hash=password_context.hash("Kahve123"),
                role=UserRole.CUSTOMER,
                preferences={"coffee_type": "LATTE", "allergens": []},
            )
            db.add(test_user)
            db.flush()
        else:
            test_user.full_name = "İzmir Kahve Test Kullanıcısı"
            test_user.email = "test@example.com"
            test_user.password_hash = password_context.hash("Kahve123")
            test_user.role = UserRole.CUSTOMER
            test_user.preferences = {"coffee_type": "LATTE", "allergens": []}

        active_subscription = db.scalar(
            select(Subscription).where(
                Subscription.user_id == test_user.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        if active_subscription is None:
            db.add(
                Subscription(
                    user_id=test_user.id,
                    plan_type="STARTER",
                    remaining_credits=10,
                    status=SubscriptionStatus.ACTIVE,
                    started_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=30),
                )
            )

        shop_owner = db.scalar(select(User).where(User.phone_number == "05551112244"))
        if shop_owner is None:
            shop_owner = User(
                phone_number="05551112244",
                full_name="KahveCell Test Dükkân Sahibi",
                email="shop-owner@example.com",
                role=UserRole.SHOP_OWNER,
                is_verified=True,
            )
            db.add(shop_owner)
            db.flush()
        else:
            shop_owner.full_name = "KahveCell Test Dükkân Sahibi"
            shop_owner.role = UserRole.SHOP_OWNER
            shop_owner.is_verified = True

        for shop_data in SHOPS:
            shop = db.scalar(select(Shop).where(Shop.name == shop_data["name"]))
            if shop is None:
                shop = Shop(**shop_data)
                db.add(shop)
                db.flush()
            else:
                for key, value in shop_data.items():
                    setattr(shop, key, value)

            if shop_data["name"] == "Buca Yeşil Kahve":
                shop.owner_id = shop_owner.id

            for product_name, description, base_price in PRODUCTS:
                product = db.scalar(
                    select(Product).where(
                        Product.shop_id == shop.id,
                        Product.name == product_name,
                    )
                )
                if product is None:
                    db.add(
                        Product(
                            shop_id=shop.id,
                            name=product_name,
                            description=description,
                            base_price=base_price,
                            is_available=True,
                        )
                    )
                else:
                    product.description = description
                    product.base_price = base_price
                    product.is_available = True

        db.commit()
        print("Seed tamamlandı: 5 İzmir dükkânı, 25 ürün, müşteri ve dükkân sahibi test hesapları hazır.")
        print("Telefon: 05551112233")
        print("Dükkân sahibi telefonu: 05551112244 (OTP: 1234 ile giriş)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
