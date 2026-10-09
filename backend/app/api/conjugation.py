"""HTTP endpoint for querying reviewed conjugation tables."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.contracts import ApiErrorCode, ConjugationLookupResponse
from app.domain.verb_contracts import FormId
from app.api.errors import ApiProblem
from app.services.catalog_repository import CatalogLoadError, get_catalog_repository
from app.services.conjugation_lookup import ConjugationLookupService

router = APIRouter(tags=["conjugation"])


def get_lookup_service() -> ConjugationLookupService:
    try:
        repository = get_catalog_repository()
    except CatalogLoadError as exc:
        raise ApiProblem(
            503,
            ApiErrorCode.CATALOG_NOT_READY,
            "Los datos de conjugación no superan la validación del catálogo.",
        ) from exc
    return ConjugationLookupService(repository)


@router.get(
    "/verbs/{verb_id}/conjugation",
    response_model=ConjugationLookupResponse,
    summary="Consultar tablas de conjugación aprobadas",
)
def lookup_conjugation(
    verb_id: str,
    form_id: Annotated[list[FormId] | None, Query()] = None,
    construction_id: str | None = None,
    service: ConjugationLookupService = Depends(get_lookup_service),
) -> ConjugationLookupResponse:
    """A missing form_id requests all selectable forms available for the verb."""
    return service.lookup(
        verb_id=verb_id,
        form_ids=form_id,
        construction_id=construction_id,
    )
