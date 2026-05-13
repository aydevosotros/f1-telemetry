from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from f1_telemetry.api.routes import router
from f1_telemetry.core.config import settings

app = FastAPI(title="F1 25 Telemetry API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
