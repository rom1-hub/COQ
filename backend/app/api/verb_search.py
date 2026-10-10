"""Search the approved production catalogue by infinitive prefix."""
from __future__ import annotations

import unicodedata
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.contracts import ApiErrorCode, VerbSearchItem, VerbSearchResponse
from app.api.errors import ApiProblem
from app.domain.verb_contracts import ReviewStatus
from app.services.catalog_repository import CatalogLoadError, get_catalog_repository

router = APIRouter(tags=["verbs"])


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip()).casefold()


def _is_publicly_searchable(verb: object, repository: object) -> bool:
    """Return true only when the verb, its pattern and default construction are approved."""
    if getattr(verb, "review_status", None) != ReviewStatus.APPROVED:
        return False
    if not getattr(verb, "is_approved_for_practice", False):
        return False

    pattern_id = getattr(verb, "pattern_id", None)
    if not pattern_id:
        return False
    pattern = repository.pattern_by_id(pattern_id)  # type: ignore[attr-defined]
    if pattern is None or pattern.review_status != ReviewStatus.APPROVED:
        return False

    default_construction_id = getattr(verb, "default_construction_id", None)
    return any(
        construction.construction_id == default_construction_id
        and construction.review_status == ReviewStatus.APPROVED
        for construction in getattr(verb, "constructions", ())
    )


@router.get(
    "/verbs/search",
    response_model=VerbSearchResponse,
    summary="Buscar verbos aprobados por infinitivo",
)
def search_verbs(
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    exact: bool = False,
) -> VerbSearchResponse:
    """Search canonical infinitives and registered aliases, never the candidate inventory.

    With exact=true, match the full canonical infinitive or a registered search alias;
    otherwise return exact, prefix and alias-prefix matches in stable order.
    """
    normalized_query = _normalized(q)
    if not normalized_query:
        raise ApiProblem(
            422,
            ApiErrorCode.INVALID_REQUEST,
            "El infinitivo de búsqueda no puede estar vacío.",
        )

    try:
        repository = get_catalog_repository()
    except CatalogLoadError as exc:
        raise ApiProblem(
            503,
            ApiErrorCode.CATALOG_NOT_READY,
            "Los datos de conjugación no superan la validación del catálogo.",
        ) from exc

    if not repository.production_ready:
        raise ApiProblem(
            503,
            ApiErrorCode.CATALOG_NOT_READY,
            "El catálogo de conjugación todavía no está listo para consultas.",
        )

    matches: list[tuple[int, int, str, VerbSearchItem]] = []
    for verb in repository.verbs:
        infinitive = getattr(verb, "infinitive", "")
        normalized_infinitive = _normalized(infinitive)
        aliases = tuple(_normalized(alias) for alias in getattr(verb, "search_aliases", ()))
        canonical_exact = normalized_infinitive == normalized_query
        canonical_prefix = normalized_infinitive.startswith(normalized_query)
        alias_exact = normalized_query in aliases
        alias_prefix = any(alias.startswith(normalized_query) for alias in aliases)

        if exact:
            if not (canonical_exact or alias_exact):
                continue
            match_rank = 0 if canonical_exact else 2
        else:
            if not (canonical_prefix or alias_prefix):
                continue
            if canonical_exact:
                match_rank = 0
            elif canonical_prefix:
                match_rank = 1
            elif alias_exact:
                match_rank = 2
            else:
                match_rank = 3
        if not _is_publicly_searchable(verb, repository):
            continue

        item = VerbSearchItem(
            verb_id=verb.verb_id,
            infinitive=verb.infinitive,
            label=verb.infinitive,
            group_id=verb.group_id,
            family_ids=verb.family_ids,
            default_construction_id=verb.default_construction_id,
        )
        matches.append((
            match_rank,
            len(normalized_infinitive),
            normalized_infinitive,
            item,
        ))

    matches.sort(key=lambda row: (row[0], row[1], row[2]))
    return VerbSearchResponse(
        items=[row[3] for row in matches[:limit]],
        query=q.strip(),
        limit=limit,
    )
