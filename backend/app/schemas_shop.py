from pydantic import BaseModel, ConfigDict


class ProductSummary(BaseModel):
    id: int
    name: str
    description: str | None
    base_price: float
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


class ShopSummary(BaseModel):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    opening_hours: str | None
    is_open: bool
    distance_km: float | None = None


class ShopDetail(ShopSummary):
    products: list[ProductSummary]
