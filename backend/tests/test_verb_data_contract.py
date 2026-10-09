from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.verb_contracts import (
    AvailabilityStatus,
    Auxiliary,
    COMPOUND_AUXILIARY_TENSE,
    CatalogScope,
    ConstructionKind,
    ConstructionProfile,
    EvidenceMethod,
    EvidenceScope,
    FormAvailability,
    FormContext,
    FormId,
    FormOverride,
    Gender,
    GrammaticalNumber,
    MembershipPolicy,
    ParticipleAgreementPolicy,
    PersonId,
    Regularity,
    ReviewStatus,
    ScopeKind,
    ScopeStatus,
    SourceEvidence,
    VerbGroup,
    VerbRecord,
)


def manual_evidence(*scopes: EvidenceScope) -> SourceEvidence:
    return SourceEvidence(
        source_id="academie.donner.2024",
        authority="Académie française",
        label="Entrée et tableau de conjugaison consultés manuellement",
        url="https://www.dictionnaire-academie.fr/conjuguer/A9D3041",
        method=EvidenceMethod.MANUAL_REFERENCE_CHECK,
        scopes=list(scopes or [EvidenceScope.LEMMA]),
        consulted_on=date(2026, 10, 9),
        edition="9e édition",
    )


def candidate_construction(
    *,
    kind: ConstructionKind = ConstructionKind.NON_PRONOMINAL,
    auxiliary: Auxiliary = Auxiliary.AVOIR,
    agreement: ParticipleAgreementPolicy = ParticipleAgreementPolicy.INVARIABLE,
    status: ReviewStatus = ReviewStatus.CANDIDATE,
    evidence: list[SourceEvidence] | None = None,
) -> ConstructionProfile:
    return ConstructionProfile(
        construction_id="parler.non_pronominal",
        kind=kind,
        display_infinitive="parler",
        auxiliary=auxiliary,
        participle_agreement=agreement,
        review_status=status,
        source_evidence=evidence or [],
    )


def candidate_verb(**overrides) -> VerbRecord:
    values = {
        "verb_id": "v_parler",
        "infinitive": "parler",
        "group_id": VerbGroup.FIRST,
        "family_ids": ["first_regular"],
        "pattern_id": "first_er_regular",
        "regularity": Regularity.REGULAR,
        "review_status": ReviewStatus.CANDIDATE,
        "default_construction_id": "parler.non_pronominal",
        "constructions": [candidate_construction()],
    }
    values.update(overrides)
    return VerbRecord(**values)


def test_catalogue_record_is_candidate_by_default_and_not_practice_eligible():
    verb = candidate_verb()
    assert verb.infinitive == "parler"
    assert verb.is_approved_for_practice is False
    assert verb.constructions[0].auxiliary == Auxiliary.AVOIR


def test_approved_verb_requires_evidence_group_pattern_and_approved_constructions():
    with pytest.raises(ValidationError, match="approved verbs require source evidence|reviewed verbs require source evidence"):
        candidate_verb(review_status=ReviewStatus.APPROVED)

    source = manual_evidence(EvidenceScope.LEMMA, EvidenceScope.GROUP, EvidenceScope.PATTERN)
    construction = candidate_construction(
        status=ReviewStatus.APPROVED,
        evidence=[manual_evidence(EvidenceScope.CONSTRUCTION, EvidenceScope.AUXILIARY)],
    )
    verb = candidate_verb(
        review_status=ReviewStatus.APPROVED,
        source_evidence=[source],
        constructions=[construction],
    )
    assert verb.is_approved_for_practice is True


def test_coq_auxiliary_and_agreement_policy_cannot_contradict():
    with pytest.raises(ValidationError, match="requires participle_agreement=subject"):
        candidate_construction(
            auxiliary=Auxiliary.ETRE,
            agreement=ParticipleAgreementPolicy.INVARIABLE,
        )
    with pytest.raises(ValidationError, match="does not allow pronominal construction with avoir"):
        candidate_construction(
            kind=ConstructionKind.PRONOMINAL,
            auxiliary=Auxiliary.AVOIR,
            agreement=ParticipleAgreementPolicy.INVARIABLE,
        )


def test_form_override_requires_person_for_finite_form_and_keeps_variants_exact():
    override = FormOverride(
        form_id=FormId.PRESENT_INDICATIF,
        context=FormContext(person=PersonId.JE),
        preferred_form="paie",
        alternatives=["paye"],
        review_status=ReviewStatus.FORMS_REVIEWED,
        source_evidence=[manual_evidence(EvidenceScope.FORM)],
    )
    assert override.accepted_forms == ("paie", "paye")

    with pytest.raises(ValidationError, match="requires a person context"):
        FormOverride(
            form_id=FormId.PRESENT_INDICATIF,
            preferred_form="parle",
        )


def test_nonpersonal_form_cannot_have_person_and_subjunctive_answer_is_only_verb_form():
    override = FormOverride(
        form_id=FormId.SUBJONCTIF_PRESENT,
        context=FormContext(person=PersonId.JE),
        preferred_form="sois",
    )
    assert override.preferred_form == "sois"

    with pytest.raises(ValidationError, match="does not take a person context"):
        FormOverride(
            form_id=FormId.PARTICIPE_PRESENT,
            context=FormContext(person=PersonId.JE),
            preferred_form="parlant",
        )


def test_form_context_respects_coq_on_and_vous_constraints():
    with pytest.raises(ValidationError, match="does not offer feminine-singular"):
        FormContext(person=PersonId.ON, gender=Gender.FEMININE, number=GrammaticalNumber.SINGULAR)
    with pytest.raises(ValidationError, match="reserved for singular vous"):
        FormContext(person=PersonId.VOUS, gender=Gender.MASCULINE, number=GrammaticalNumber.PLURAL, usage="courtesy")
    courtesy = FormContext(
        person=PersonId.VOUS,
        gender=Gender.FEMININE,
        number=GrammaticalNumber.SINGULAR,
        usage="courtesy",
    )
    assert courtesy.usage.value == "courtesy"


def test_unavailable_form_must_include_evidence():
    with pytest.raises(ValidationError, match="require supporting source evidence"):
        FormAvailability(
            form_id=FormId.PRESENT_INDICATIF,
            context=FormContext(person=PersonId.JE),
            status=AvailabilityStatus.UNAVAILABLE,
            reason="Forma no usada según la fuente",
        )
    item = FormAvailability(
        form_id=FormId.PRESENT_INDICATIF,
        context=FormContext(person=PersonId.JE),
        status=AvailabilityStatus.UNAVAILABLE,
        reason="Forma no usada según la fuente",
        source_evidence=[manual_evidence(EvidenceScope.AVAILABILITY)],
    )
    assert item.status == AvailabilityStatus.UNAVAILABLE


def test_curated_common_100_is_not_a_morphological_family_and_stays_planned():
    collection = CatalogScope(
        scope_id="collection:common_100",
        kind=ScopeKind.COLLECTION,
        label_es="100 verbos más comunes (por definir)",
        membership_policy=MembershipPolicy.EXPLICIT_VERB_IDS,
        status=ScopeStatus.PLANNED,
        display_order=16,
    )
    assert collection.status == ScopeStatus.PLANNED
    assert collection.group_id is None
    with pytest.raises(ValidationError, match="active collection requires explicit members"):
        CatalogScope(
            scope_id="collection:common_100",
            kind=ScopeKind.COLLECTION,
            label_es="100 verbos más comunes",
            membership_policy=MembershipPolicy.EXPLICIT_VERB_IDS,
            status=ScopeStatus.ACTIVE,
            display_order=16,
        )


def test_morphological_family_requires_group_and_explicit_membership():
    family = CatalogScope(
        scope_id="family:ger",
        kind=ScopeKind.FAMILY,
        label_es="GER",
        label_fr="-GER",
        group_id=VerbGroup.FIRST,
        membership_policy=MembershipPolicy.REGISTERED_PATTERNS,
        pattern_ids=["first_group_ger"],
        status=ScopeStatus.ACTIVE,
        display_order=3,
    )
    assert family.group_id == VerbGroup.FIRST
    with pytest.raises(ValidationError, match="pattern-based family requires pattern_ids"):
        CatalogScope(
            scope_id="family:ger",
            kind=ScopeKind.FAMILY,
            label_es="GER",
            group_id=VerbGroup.FIRST,
            membership_policy=MembershipPolicy.REGISTERED_PATTERNS,
            status=ScopeStatus.ACTIVE,
            display_order=3,
        )


def test_academie_reference_audit_cannot_be_recorded_as_automated_scraping():
    # The evidence contract only permits explicit manual review or license-based data sources.
    with pytest.raises(ValidationError):
        SourceEvidence(
            source_id="academie.scrape",
            authority="Académie française",
            label="Extracción masiva",
            url="https://www.dictionnaire-academie.fr/",
            method="automated_scraping",
            scopes=[EvidenceScope.FORM],
        )


def test_pydantic_schemas_are_committed_and_match_contract_documents():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    schema_dir = root / "data" / "catalogs"
    for filename in (
        "verb-record.schema.json",
        "conjugation-pattern.schema.json",
        "catalog-scope.schema.json",
        "candidate-infinitive.schema.json",
    ):
        schema = json.loads((schema_dir / filename).read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "title" in schema
    contract_doc = (root / "docs" / "DATA-CONTRACT.md").read_text(encoding="utf-8")
    assert "## 2. Entidades" in contract_doc
    assert "## 7. Puertas de calidad" in contract_doc
    source_audit = (root / "docs" / "DATA-SOURCE-AUDIT.md").read_text(encoding="utf-8")
    assert "no desarrollará un scraper" in source_audit


def test_compound_tense_recipes_are_complete_and_match_the_approved_linguistic_contract():
    assert set(COMPOUND_AUXILIARY_TENSE) == {
        FormId.PASSE_COMPOSE, FormId.PLUS_QUE_PARFAIT, FormId.CONDITIONNEL_PASSE,
        FormId.FUTUR_ANTERIEUR, FormId.SUBJONCTIF_PASSE,
    }
    assert COMPOUND_AUXILIARY_TENSE == {
        FormId.PASSE_COMPOSE: FormId.PRESENT_INDICATIF,
        FormId.PLUS_QUE_PARFAIT: FormId.IMPARFAIT,
        FormId.CONDITIONNEL_PASSE: FormId.CONDITIONNEL_PRESENT,
        FormId.FUTUR_ANTERIEUR: FormId.FUTUR_SIMPLE,
        FormId.SUBJONCTIF_PASSE: FormId.SUBJONCTIF_PRESENT,
    }


def test_compound_form_override_requires_gender_and_number_context():
    with pytest.raises(ValidationError, match="compound forms require an explicit gender/number"):
        FormOverride(
            form_id=FormId.PASSE_COMPOSE,
            context=FormContext(person=PersonId.JE),
            preferred_form="ai parlé",
        )
    override = FormOverride(
        form_id=FormId.PASSE_COMPOSE,
        context=FormContext(
            person=PersonId.JE,
            gender=Gender.FEMININE,
            number=GrammaticalNumber.SINGULAR,
        ),
        preferred_form="ai parlé",
    )
    assert override.context.gender == Gender.FEMININE


def test_vous_context_requires_explicit_courtesy_or_plural_use():
    with pytest.raises(ValidationError, match="singular vous requires courtesy usage"):
        FormContext(person=PersonId.VOUS, gender=Gender.MASCULINE, number=GrammaticalNumber.SINGULAR)
    with pytest.raises(ValidationError, match="vous requires explicit courtesy or standard usage"):
        FormContext(person=PersonId.VOUS)

    # Simple forms need usage metadata, but not agreement gender/number.
    courtesy_simple = FormContext(person=PersonId.VOUS, usage="courtesy")
    plural_simple = FormContext(person=PersonId.VOUS, usage="standard")
    assert courtesy_simple.gender is None and courtesy_simple.number is None
    assert plural_simple.gender is None and plural_simple.number is None

    plural_compound = FormContext(
        person=PersonId.VOUS,
        gender=Gender.MASCULINE,
        number=GrammaticalNumber.PLURAL,
        usage="standard",
    )
    assert plural_compound.number == GrammaticalNumber.PLURAL
