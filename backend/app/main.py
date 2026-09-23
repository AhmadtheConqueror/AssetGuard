from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai_analyses import router as ai_analyses_router
from app.api.alerts import router as alerts_router
from app.api.auth import router as auth_router
from app.api.assets import router as assets_router
from app.api.maintenance_records import router as maintenance_records_router
from app.api.ingestion import router as ingestion_router
from app.api.sensor_readings import router as sensor_readings_router
from app.api.sensors import router as sensors_router
from app.api.users import router as users_router

app = FastAPI(
    title="AssetGuard API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(sensors_router)
app.include_router(sensor_readings_router)
app.include_router(ai_analyses_router)
app.include_router(alerts_router)
app.include_router(maintenance_records_router)
app.include_router(ingestion_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
