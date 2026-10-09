"""Regression review for the COQ `parler` pilot.

All records created here are synthetic test fixtures. This module does not add
or approve a production verb or pattern.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.conjugation import get_lookup_service
from app.domain.verb_contracts import (
    Auxiliary,
    ConstructionKind,
    ConstructionProfile,
    ConjugationPattern,
    EvidenceMethod,
    EvidenceScope,
    FormId,
    ParticipleAgreementPolicy,
    Regularity,
    ReviewStatus,
    SourceEvidence,
    VerbGroup,
    VerbRecord,
)
from app.main import app
from app.services.conjugation_lookup import ConjugationLookupService


class _MemoryRepository:
    """An isolated in-memory repository used only by this test module."""

    production_ready = True

    def __init__(self, verb: VerbRecord, pattern: ConjugationPattern) -> None:
        self._verb = verb
        self._pattern = pattern

    def verb_by_id(self, verb_id: str) -> VerbRecord | None:
        return self._verb if verb_id == self._verb.verb_id else None

    def pattern_by_id(self, pattern_id: str) -> ConjugationPattern | None:
        return self._pattern if pattern_id == self._pattern.pattern_id else None


def _test_evidence(scope: EvidenceScope) -> SourceEvidence:
    return SourceEvidence(
        source_id=f"test.parler-pilot.{scope.value}",
        authority="COQ automated test fixture",
        label="Synthetic test record; not production evidence",
        method=EvidenceMethod.COQ_RULE_REVIEW,
        scopes=[scope],
        decision_id="TEST-PARLER-PILOT-001",
    )


def _approved_test_records() -> tuple[VerbRecord, ConjugationPattern]:
    pattern = ConjugationPattern(
        pattern_id="first_er_regular",
        group_id=VerbGroup.FIRST,
        family_id="first_regular",
        algorithm_key="first_group_regular_er",
        algorithm_version=1,
        review_status=ReviewStatus.APPROVED,
        source_evidence=[_test_evidence(EvidenceScope.PATTERN)],
    )
    construction = ConstructionProfile(
        construction_id="parler.non_pronominal",
        kind=ConstructionKind.NON_PRONOMINAL,
        display_infinitive="parler",
        auxiliary=Auxiliary.AVOIR,
        participle_agreement=ParticipleAgreementPolicy.INVARIABLE,
        review_status=ReviewStatus.APPROVED,
        source_evidence=[_test_evidence(EvidenceScope.CONSTRUCTION)],
    )
    verb = VerbRecord(
        verb_id="v_parler",
        infinitive="parler",
        group_id=VerbGroup.FIRST,
        family_ids=["first_regular"],
        pattern_id="first_er_regular",
        regularity=Regularity.REGULAR,
        review_status=ReviewStatus.APPROVED,
        default_construction_id="parler.non_pronominal",
        constructions=[construction],
        source_evidence=[_test_evidence(EvidenceScope.LEMMA)],
    )
    return verb, pattern


@pytest.fixture
def client():
    verb, pattern = _approved_test_records()
    repository = _MemoryRepository(verb, pattern)
    service = ConjugationLookupService(repository)  # type: ignore[arg-type]
    app.dependency_overrides[get_lookup_service] = lambda: service
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _row(rows: list[dict], *, person: str | None, **context_values: str) -> dict:
    for item in rows:
        context = item["context"]
        if item["person"] != person:
            continue
        if all(context.get(key) == value for key, value in context_values.items()):
            return item
    raise AssertionError(f"No row for person={person!r}, context={context_values!r}")


# Each of COQ's 13 selectable forms is checked through the real HTTP route and
# the production ConjugationEngine, using only in-memory synthetic records.
@pytest.mark.parametrize(
    ("form_id", "person", "context_values", "expected", "row_count"),
    [
        (FormId.PRESENT_INDICATIF, "je", {}, "parle", 9),
        (FormId.IMPERATIF_PRESENT, "tu", {}, "parle", 3),
        (FormId.IMPARFAIT, "nous", {}, "parlions", 9),
        (FormId.CONDITIONNEL_PRESENT, "nous", {}, "parlerions", 9),
        (FormId.FUTUR_SIMPLE, "nous", {}, "parlerons", 9),
        (FormId.SUBJONCTIF_PRESENT, "nous", {}, "parlions", 9),
        (
            FormId.PASSE_COMPOSE,
            "je",
            {"gender": "masculine", "number": "singular"},
            "ai parlé",
            17,
        ),
        (
            FormId.PLUS_QUE_PARFAIT,
            "je",
            {"gender": "masculine", "number": "singular"},
            "avais parlé",
            17,
        ),
        (
            FormId.CONDITIONNEL_PASSE,
            "je",
            {"gender": "masculine", "number": "singular"},
            "aurais parlé",
            17,
        ),
        (
            FormId.FUTUR_ANTERIEUR,
            "je",
            {"gender": "masculine", "number": "singular"},
            "aurai parlé",
            17,
        ),
        (
            FormId.SUBJONCTIF_PASSE,
            "je",
            {"gender": "masculine", "number": "singular"},
            "aie parlé",
            17,
        ),
        (FormId.PARTICIPE_PRESENT, None, {}, "parlant", 1),
        (FormId.GERONDIF_PRESENT, None, {}, "en parlant", 1),
    ],
)
def test_parler_pilot_all_13_selectable_forms(
    client: TestClient,
    form_id: FormId,
    person: str | None,
    context_values: dict[str, str],
    expected: str,
    row_count: int,
) -> None:
    response = client.get(
        "/api/v1/verbs/v_parler/conjugation",
        params=[("form_id", form_id.value)],
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["verb_id"] == "v_parler"
    assert len(payload["tables"]) == 1
    rows = payload["tables"][0]["rows"]
    assert len(rows) == row_count
    selected = _row(rows, person=person, **context_values)
    assert selected["display_forms"] == [expected]


def test_parler_pilot_maps_on_to_third_person_forms_for_all_simple_forms(client: TestClient) -> None:
    examples = {
        FormId.PRESENT_INDICATIF: "parle",
        FormId.IMPARFAIT: "parlait",
        FormId.CONDITIONNEL_PRESENT: "parlerait",
        FormId.FUTUR_SIMPLE: "parlera",
        FormId.SUBJONCTIF_PRESENT: "parle",
    }
    for form_id, expected in examples.items():
        response = client.get(
            "/api/v1/verbs/v_parler/conjugation",
            params=[("form_id", form_id.value)],
        )
        assert response.status_code == 200, response.text
        rows = response.json()["tables"][0]["rows"]
        assert _row(rows, person="on")["display_forms"] == [expected]


def test_parler_pilot_keeps_avoir_participle_invariable_in_all_compound_contexts(
    client: TestClient,
) -> None:
    auxiliary_forms = {
        FormId.PASSE_COMPOSE: "avez parlé",
        FormId.PLUS_QUE_PARFAIT: "aviez parlé",
        FormId.CONDITIONNEL_PASSE: "auriez parlé",
        FormId.FUTUR_ANTERIEUR: "aurez parlé",
        FormId.SUBJONCTIF_PASSE: "ayez parlé",
    }
    for form_id, expected_vous in auxiliary_forms.items():
        response = client.get(
            "/api/v1/verbs/v_parler/conjugation",
            params=[("form_id", form_id.value)],
        )
        assert response.status_code == 200, response.text
        rows = response.json()["tables"][0]["rows"]

        for gender, number in (
            ("masculine", "singular"),
            ("masculine", "plural"),
            ("feminine", "plural"),
        ):
            on_row = _row(
                rows,
                person="on",
                gender=gender,
                number=number,
            )
            assert on_row["display_forms"] == [
                {
                    FormId.PASSE_COMPOSE: "a parlé",
                    FormId.PLUS_QUE_PARFAIT: "avait parlé",
                    FormId.CONDITIONNEL_PASSE: "aurait parlé",
                    FormId.FUTUR_ANTERIEUR: "aura parlé",
                    FormId.SUBJONCTIF_PASSE: "ait parlé",
                }[form_id]
            ]

        courtesy_vous = _row(
            rows,
            person="vous",
            usage="courtesy",
            gender="feminine",
            number="singular",
        )
        plural_vous = _row(
            rows,
            person="vous",
            usage="standard",
            gender="feminine",
            number="plural",
        )
        assert courtesy_vous["display_forms"] == [expected_vous]
        assert plural_vous["display_forms"] == [expected_vous]
