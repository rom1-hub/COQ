from fastapi import APIRouter
from pydantic import BaseModel

from app.domain.conjugation_engine import ConjugationEngine  # noqa: F401
from app.services.catalog_repository import CatalogLoadError, get_catalog_repository

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    project: str
    api_version: str
    linguistic_contracts_approved: bool
    conjugation_engine_available: bool
    production_catalog_ready: bool


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Separate process health from production-data readiness."""
    try:
        catalog_ready = get_catalog_repository().production_ready
    except CatalogLoadError:
        catalog_ready = False

    return HealthResponse(
        status="ok",
        project="coq",
        api_version="0.2.0",
        linguistic_contracts_approved=False,
        conjugation_engine_available=True,
        production_catalog_ready=catalog_ready,
    )
