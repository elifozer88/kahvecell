from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Shop
from app.schemas_shop import ShopDetail, ShopSummary

router = APIRouter(prefix="/api/v1/shops", tags=["Shops"])


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki koordinat arasındaki kuş uçuşu mesafeyi kilometre olarak döndürür."""
    earth_radius_km = 6371.0
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    value = (
        sin(delta_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(value))


def to_summary(shop: Shop, distance_km: float | None = None) -> ShopSummary:
    return ShopSummary(
        id=shop.id,
        name=shop.name,
        address=shop.address,
        latitude=shop.latitude,
        longitude=shop.longitude,
        opening_hours=shop.opening_hours,
        is_open=shop.is_open,
        distance_km=round(distance_km, 2) if distance_km is not None else None,
    )


@router.get("", response_model=list[ShopSummary])
def list_shops(
    q: str | None = Query(default=None, description="Dükkân adı veya adresinde ara"),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=500),
    is_open: bool | None = Query(default=None, description="Açık/kapalı filtrele"),
    db: Session = Depends(get_db),
):
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Yakınlık sıralaması için latitude ve longitude birlikte verilmelidir")

    statement = select(Shop)
    if q:
        search = f"%{q.strip()}%"
        statement = statement.where(Shop.name.ilike(search) | Shop.address.ilike(search))
    if is_open is not None:
        statement = statement.where(Shop.is_open == is_open)

    shops = list(db.scalars(statement).all())
    results: list[tuple[Shop, float | None]] = []
    for shop in shops:
        distance = None
        if latitude is not None and longitude is not None:
            distance = haversine_km(latitude, longitude, shop.latitude, shop.longitude)
            if radius_km is not None and distance > radius_km:
                continue
        results.append((shop, distance))

    if latitude is not None:
        results.sort(key=lambda item: (item[1], item[0].name))
    else:
        results.sort(key=lambda item: item[0].name.casefold())
    return [to_summary(shop, distance) for shop, distance in results]


@router.get("/{shop_id}", response_model=ShopDetail)
def get_shop_detail(shop_id: int, db: Session = Depends(get_db)):
    shop = db.scalar(
        select(Shop)
        .options(selectinload(Shop.products))
        .where(Shop.id == shop_id)
    )
    if shop is None:
        raise HTTPException(status_code=404, detail="Dükkân bulunamadı")

    return ShopDetail(
        **to_summary(shop).model_dump(),
        products=shop.products,
    )
