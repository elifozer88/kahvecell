from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401
from app.migrations import ensure_current_schema
from app.routers.auth import router as auth_router
from app.routers.subscriptions import router as subscriptions_router
from app.routers.shops import router as shops_router
from app.routers.orders import router as orders_router


app = FastAPI(
    title="KahveCell API",
    version="0.1.0",
)

@app.on_event("startup")
def create_database_tables():
    ensure_current_schema()
    Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(subscriptions_router)
app.include_router(shops_router)
app.include_router(orders_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"message": "KahveCell backend ayakta!"}


@app.get("/api/v1/health")
def api_health_check():
    return {"status": "ok", "service": "KahveCell API"}
