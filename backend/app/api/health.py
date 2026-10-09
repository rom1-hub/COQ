from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    project: str
    api_version: str
    linguistic_contracts_approved: bool
    conjugation_engine_available: bool


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report service status without pretending that conjugation is implemented."""
    return HealthResponse(
        status="ok",
        project="coq",
        api_version="0.1.0",
        linguistic_contracts_approved=False,
        conjugation_engine_available=False,
    )
