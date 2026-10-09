from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router

app = FastAPI(
    title="COQ API",
    description=(
        "API del proyecto nuevo de conjugación. El motor lingüístico y los "
        "endpoints de conjugación permanecerán ausentes hasta aprobar los contratos."
    ),
    version="0.1.0",
)

# Production origins must be set from deployment configuration before API integration.
# During the local prototype phase, the allowlist is intentionally minimal.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health_router, prefix="/api/v1")
