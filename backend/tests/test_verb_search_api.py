from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import verb_search
from app.domain.verb_contracts import (
    Auxiliary,
    ConstructionKind,
    ConstructionProfile,
    ConjugationPattern,
    EvidenceMethod,
    EvidenceScope,
    ParticipleAgreementPolicy,
    Regularity,
    ReviewStatus,
    SourceEvidence,
    VerbGroup,
    VerbRecord,
)
from app.main import app


def _evidence(scope: EvidenceScope) -> SourceEvidence:
    return SourceEvidence(
        source_id=f"test.verb-search.{scope.value}",
        authority="COQ automated test fixture",
        label="Synthetic test fixture; not production evidence",
        method=EvidenceMethod.COQ_RULE_REVIEW,
        scopes=[scope],
        decision_id="TEST-VERB-SEARCH-001",
    )


def _approved_records() -> tuple[VerbRecord, ConjugationPattern]:
    pattern = ConjugationPattern(
        pattern_id="first_er_regular",
        group_id=VerbGroup.FIRST,
        family_id="first_regular",
        algorithm_key="first_group_regular_er",
        algorithm_version=1,
        review_status=ReviewStatus.APPROVED,
        source_evidence=[_evidence(EvidenceScope.PATTERN)],
    )
    construction = ConstructionProfile(
        construction_id="parler.non_pronominal",
        kind=ConstructionKind.NON_PRONOMINAL,
        display_infinitive="parler",
        auxiliary=Auxiliary.AVOIR,
        participle_agreement=ParticipleAgreementPolicy.INVARIABLE,
        review_status=ReviewStatus.APPROVED,
        source_evidence=[_evidence(EvidenceScope.CONSTRUCTION)],
    )
    verb = VerbRecord(
        verb_id="v_parler",
        infinitive="parler",
        search_aliases=["parlo"],
        group_id=VerbGroup.FIRST,
        family_ids=["first_regular"],
        pattern_id="first_er_regular",
        regularity=Regularity.REGULAR,
        review_status=ReviewStatus.APPROVED,
        default_construction_id="parler.non_pronominal",
        constructions=[construction],
        source_evidence=[_evidence(EvidenceScope.LEMMA)],
    )
    return verb, pattern


class _Repository:
    def __init__(self, ready: bool) -> None:
        self.production_ready = ready
        verb, pattern = _approved_records()
        candidate = verb.model_copy(update={
            "verb_id": "v_parlo",
            "infinitive": "parlo",
            "search_aliases": [],
            "review_status": ReviewStatus.CANDIDATE,
        })
        self.verbs = (verb, candidate) if ready else ()
        self._patterns = {pattern.pattern_id: pattern}

    def pattern_by_id(self, pattern_id: str):
        return self._patterns.get(pattern_id)


def test_verb_search_returns_exact_approved_infinitive(monkeypatch) -> None:
    monkeypatch.setattr(verb_search, "get_catalog_repository", lambda: _Repository(ready=True))
    with TestClient(app) as client:
        response = client.get("/api/v1/verbs/search", params={"q": "PARLER", "limit": 10, "exact": True})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["query"] == "PARLER"
    assert payload["limit"] == 10
    assert [item["infinitive"] for item in payload["items"]] == ["parler"]
    assert payload["items"][0]["verb_id"] == "v_parler"
    assert payload["items"][0]["default_construction_id"] == "parler.non_pronominal"


def test_verb_search_fails_closed_when_catalog_is_not_ready(monkeypatch) -> None:
    monkeypatch.setattr(verb_search, "get_catalog_repository", lambda: _Repository(ready=False))
    with TestClient(app) as client:
        response = client.get("/api/v1/verbs/search", params={"q": "parler"})

    assert response.status_code == 503
    assert response.json()["code"] == "CATALOG_NOT_READY"


def test_verb_search_rejects_blank_query(monkeypatch) -> None:
    monkeypatch.setattr(verb_search, "get_catalog_repository", lambda: _Repository(ready=True))
    with TestClient(app) as client:
        response = client.get("/api/v1/verbs/search", params={"q": "   "})

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REQUEST"


def test_verb_search_resolves_registered_alias_only_when_exact_is_requested(monkeypatch) -> None:
    monkeypatch.setattr(verb_search, "get_catalog_repository", lambda: _Repository(ready=True))
    with TestClient(app) as client:
        exact = client.get("/api/v1/verbs/search", params={"q": "parlo", "exact": True})
        prefix = client.get("/api/v1/verbs/search", params={"q": "parlo", "exact": False})

    assert exact.status_code == 200, exact.text
    assert [item["infinitive"] for item in exact.json()["items"]] == ["parler"]
    assert prefix.status_code == 200, prefix.text
    assert [item["infinitive"] for item in prefix.json()["items"]] == ["parler"]


def test_verb_search_never_returns_unapproved_records(monkeypatch) -> None:
    monkeypatch.setattr(verb_search, "get_catalog_repository", lambda: _Repository(ready=True))
    with TestClient(app) as client:
        response = client.get("/api/v1/verbs/search", params={"q": "parl", "exact": False})

    assert response.status_code == 200, response.text
    assert [item["infinitive"] for item in response.json()["items"]] == ["parler"]
