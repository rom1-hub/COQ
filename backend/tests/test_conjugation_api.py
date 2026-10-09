from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.conjugation import get_lookup_service
from app.domain.verb_contracts import (
    Auxiliary,
    ConstructionKind,
    ConstructionProfile,
    ConjugationPattern,
    EvidenceMethod,
    EvidenceScope,
    FormContext,
    ParticipleAgreementPolicy,
    Regularity,
    ReviewStatus,
    SourceEvidence,
    VerbGroup,
    VerbRecord,
)
from app.main import app
from app.services.conjugation_lookup import ConjugationLookupService


def evidence(scope: EvidenceScope) -> SourceEvidence:
    return SourceEvidence(
        source_id=f"test.api.{scope.value}",
        authority="COQ API test fixture",
        label="Synthetic test evidence; not production data",
        method=EvidenceMethod.COQ_RULE_REVIEW,
        scopes=[scope],
        decision_id="TEST-API-001",
    )


class MemoryRepository:
    def __init__(self, verb: VerbRecord | None, pattern: ConjugationPattern, *, ready: bool = True) -> None:
        self.production_ready = ready
        self.verb = verb
        self.pattern = pattern

    def verb_by_id(self, verb_id: str) -> VerbRecord | None:
        if self.verb and self.verb.verb_id == verb_id:
            return self.verb
        return None

    def pattern_by_id(self, pattern_id: str) -> ConjugationPattern | None:
        if self.pattern.pattern_id == pattern_id:
            return self.pattern
        return None


def fixture_records(
    infinitive: str = "parler",
    *,
    auxiliary: Auxiliary = Auxiliary.AVOIR,
    verb_status: ReviewStatus = ReviewStatus.APPROVED,
) -> tuple[VerbRecord, ConjugationPattern]:
    pattern = ConjugationPattern(
        pattern_id="first_er_regular",
        group_id=VerbGroup.FIRST,
        family_id="first_regular",
        algorithm_key="first_group_regular_er",
        algorithm_version=1,
        review_status=ReviewStatus.APPROVED,
        source_evidence=[evidence(EvidenceScope.PATTERN)],
    )
    construction_id = f"{infinitive}.non_pronominal"
    construction = ConstructionProfile(
        construction_id=construction_id,
        kind=ConstructionKind.NON_PRONOMINAL,
        display_infinitive=infinitive,
        auxiliary=auxiliary,
        participle_agreement=(
            ParticipleAgreementPolicy.INVARIABLE
            if auxiliary == Auxiliary.AVOIR
            else ParticipleAgreementPolicy.SUBJECT
        ),
        review_status=ReviewStatus.APPROVED,
        source_evidence=[evidence(EvidenceScope.CONSTRUCTION)],
    )
    verb = VerbRecord(
        verb_id=f"v_{infinitive}",
        infinitive=infinitive,
        group_id=VerbGroup.FIRST,
        family_ids=["first_regular"],
        pattern_id=pattern.pattern_id,
        regularity=Regularity.REGULAR,
        review_status=verb_status,
        default_construction_id=construction_id,
        constructions=[construction],
        source_evidence=[evidence(EvidenceScope.LEMMA)],
    )
    return verb, pattern


def make_client(verb: VerbRecord | None, pattern: ConjugationPattern, *, ready: bool = True) -> TestClient:
    service = ConjugationLookupService(MemoryRepository(verb, pattern, ready=ready))  # type: ignore[arg-type]
    app.dependency_overrides[get_lookup_service] = lambda: service
    return TestClient(app)


def test_lookup_endpoint_generates_a_table_through_the_real_engine() -> None:
    verb, pattern = fixture_records()
    client = make_client(verb, pattern)
    try:
        response = client.get(
            "/api/v1/verbs/v_parler/conjugation",
            params=[("form_id", "present_indicatif")],
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["verb_id"] == "v_parler"
        assert len(payload["tables"]) == 1
        rows = payload["tables"][0]["rows"]
        assert len(rows) == 9
        assert next(row for row in rows if row["person"] == "je")["display_forms"] == ["parle"]
    finally:
        app.dependency_overrides.clear()


def test_lookup_endpoint_builds_explicit_agreement_contexts_for_compounds() -> None:
    verb, pattern = fixture_records("entrer", auxiliary=Auxiliary.ETRE)
    client = make_client(verb, pattern)
    try:
        response = client.get(
            "/api/v1/verbs/v_entrer/conjugation",
            params=[("form_id", "passe_compose")],
        )
        assert response.status_code == 200
        rows = response.json()["tables"][0]["rows"]
        assert len(rows) == 17

        courtesy_feminine = next(
            row for row in rows
            if row["person"] == "vous"
            and row["context"]["usage"] == "courtesy"
            and row["context"]["gender"] == "feminine"
        )
        plural_feminine = next(
            row for row in rows
            if row["person"] == "vous"
            and row["context"]["usage"] == "standard"
            and row["context"]["gender"] == "feminine"
        )

        assert courtesy_feminine["display_forms"] == ["\u00eates entr\u00e9e"]
        assert plural_feminine["display_forms"] == ["\u00eates entr\u00e9es"]
    finally:
        app.dependency_overrides.clear()



def test_lookup_imperative_only_returns_tu_nous_vous() -> None:
    verb, pattern = fixture_records()
    client = make_client(verb, pattern)
    try:
        response = client.get(
            "/api/v1/verbs/v_parler/conjugation",
            params=[("form_id", "imperatif_present")],
        )
        assert response.status_code == 200
        rows = response.json()["tables"][0]["rows"]
        assert [row["person"] for row in rows] == ["tu", "nous", "vous"]
        assert [row["display_forms"][0] for row in rows] == ["parle", "parlons", "parlez"]
    finally:
        app.dependency_overrides.clear()

def test_lookup_refuses_to_operate_until_catalogue_is_ready() -> None:
    verb, pattern = fixture_records()
    client = make_client(verb, pattern, ready=False)
    try:
        response = client.get(
            "/api/v1/verbs/v_parler/conjugation",
            params=[("form_id", "present_indicatif")],
        )
        assert response.status_code == 503
        assert response.json()["code"] == "CATALOG_NOT_READY"
    finally:
        app.dependency_overrides.clear()


def test_lookup_does_not_expose_unapproved_verb() -> None:
    verb, pattern = fixture_records(verb_status=ReviewStatus.CANDIDATE)
    client = make_client(verb, pattern)
    try:
        response = client.get(
            "/api/v1/verbs/v_parler/conjugation",
            params=[("form_id", "present_indicatif")],
        )
        assert response.status_code == 409
        assert response.json()["code"] == "VERB_NOT_APPROVED"
    finally:
        app.dependency_overrides.clear()
