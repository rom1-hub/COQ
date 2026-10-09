from __future__ import annotations

import pytest
from app.domain.conjugation_engine import (
    ConjugationEngine,
    FormNotReviewedError,
    FormUnavailableError,
    InvalidFormContextError,
    PatternMismatchError,
    UnapprovedRecordError,
    UnsupportedPatternError,
)
from app.domain.verb_contracts import (
    AvailabilityStatus,
    Auxiliary,
    ConstructionKind,
    ConjugationPattern,
    ConstructionProfile,
    EvidenceMethod,
    EvidenceScope,
    FormAvailability,
    FormContext,
    FormId,
    FormOverride,
    Gender,
    GrammaticalNumber,
    ParticipleAgreementPolicy,
    PersonId,
    Regularity,
    ReviewStatus,
    SourceEvidence,
    VerbGroup,
    VerbRecord,
    Usage,
)


ENGINE = ConjugationEngine()


def evidence(*scopes: EvidenceScope) -> SourceEvidence:
    return SourceEvidence(
        source_id="test.coq.engine",
        authority="COQ test fixture",
        label="Synthetic test fixture; not production evidence",
        method=EvidenceMethod.COQ_RULE_REVIEW,
        scopes=list(scopes or [EvidenceScope.FORM]),
        decision_id="TEST-ENGINE-001",
    )


def approved_pattern(*, algorithm_key: str = "first_group_regular_er", pattern_id: str = "first_er_regular") -> ConjugationPattern:
    return ConjugationPattern(
        pattern_id=pattern_id,
        group_id=VerbGroup.FIRST,
        family_id="first_regular",
        algorithm_key=algorithm_key,
        algorithm_version=1,
        review_status=ReviewStatus.APPROVED,
        source_evidence=[evidence(EvidenceScope.PATTERN)],
    )


def make_verb(
    infinitive: str = "parler",
    *,
    auxiliary: Auxiliary | None = None,
    construction_kind: ConstructionKind = ConstructionKind.NON_PRONOMINAL,
    review_status: ReviewStatus = ReviewStatus.APPROVED,
    pattern_id: str = "first_er_regular",
    algorithm_key: str = "first_group_regular_er",
    agreement: ParticipleAgreementPolicy | None = None,
    overrides: list[FormOverride] | None = None,
    availability: list[FormAvailability] | None = None,
    traits: list[str] | None = None,
    display_infinitive: str | None = None,
) -> tuple[VerbRecord, ConjugationPattern, str]:
    if auxiliary is None:
        auxiliary = Auxiliary.ETRE if construction_kind == ConstructionKind.PRONOMINAL else Auxiliary.AVOIR
    if agreement is None:
        agreement = (
            ParticipleAgreementPolicy.VERB_SPECIFIC
            if construction_kind == ConstructionKind.PRONOMINAL
            else ParticipleAgreementPolicy.INVARIABLE
            if auxiliary == Auxiliary.AVOIR
            else ParticipleAgreementPolicy.SUBJECT
        )
    construction_id = f"{infinitive}.{'pronominal' if construction_kind == ConstructionKind.PRONOMINAL else 'non_pronominal'}"
    if display_infinitive is None:
        display_infinitive = f"se {infinitive}" if construction_kind == ConstructionKind.PRONOMINAL else infinitive
    construction = ConstructionProfile(
        construction_id=construction_id,
        kind=construction_kind,
        display_infinitive=display_infinitive,
        auxiliary=auxiliary,
        participle_agreement=agreement,
        review_status=ReviewStatus.APPROVED,
        form_overrides=list(overrides or []),
        availability_overrides=list(availability or []),
        source_evidence=[evidence(EvidenceScope.CONSTRUCTION, EvidenceScope.AUXILIARY, EvidenceScope.AGREEMENT)],
    )
    verb = VerbRecord(
        verb_id=f"v_{infinitive}",
        infinitive=infinitive,
        group_id=VerbGroup.FIRST,
        family_ids=["first_regular"],
        pattern_id=pattern_id,
        regularity=Regularity.REGULAR,
        traits=list(traits or []),
        review_status=review_status,
        default_construction_id=construction_id,
        constructions=[construction],
        source_evidence=[evidence(EvidenceScope.LEMMA, EvidenceScope.GROUP, EvidenceScope.PATTERN)],
    )
    pattern = approved_pattern(algorithm_key=algorithm_key, pattern_id=pattern_id)
    return verb, pattern, construction_id


def context(person: PersonId, gender: Gender | None = None, number: GrammaticalNumber | None = None, usage=None) -> FormContext:
    values = {"person": person}
    if gender is not None:
        values["gender"] = gender
        values["number"] = number
    if usage is not None:
        values["usage"] = usage
    elif person == PersonId.VOUS:
        # Test fixtures must make the vous use explicit, just like production callers.
        values["usage"] = Usage.STANDARD
    return FormContext(**values)


def test_vous_courtesy_is_explicit_in_simple_forms_without_agreement_context():
    verb, pattern, construction_id = make_verb()
    courtesy = context(PersonId.VOUS, usage=Usage.COURTESY)

    result = ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, courtesy)

    assert result.preferred_form == "parlez"
    assert result.context.usage == Usage.COURTESY
    assert result.context.gender is None
    assert result.context.number is None


def test_vous_courtesy_compound_uses_singular_agreement_context():
    verb, pattern, construction_id = make_verb("arriver", auxiliary=Auxiliary.ETRE)
    courtesy_feminine = context(
        PersonId.VOUS, Gender.FEMININE, GrammaticalNumber.SINGULAR, Usage.COURTESY
    )
    plural_feminine = context(
        PersonId.VOUS, Gender.FEMININE, GrammaticalNumber.PLURAL, Usage.STANDARD
    )

    assert ENGINE.generate(
        verb, pattern, construction_id, FormId.PASSE_COMPOSE, courtesy_feminine
    ).preferred_form == "êtes arrivée"
    assert ENGINE.generate(
        verb, pattern, construction_id, FormId.PASSE_COMPOSE, plural_feminine
    ).preferred_form == "êtes arrivées"


def test_se_ficher_is_not_elided_and_uses_only_its_registered_display_infinitive():
    verb, pattern, construction_id = make_verb(
        "ficher",
        construction_kind=ConstructionKind.PRONOMINAL,
        display_infinitive="se ficher",
    )

    assert verb.constructions[0].display_infinitive == "se ficher"
    assert ENGINE.generate(
        verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE)
    ).preferred_form == "me fiche"


def test_regular_er_present_indicative_all_nine_ui_subjects():
    verb, pattern, construction_id = make_verb()
    expected = {
        PersonId.JE: "parle", PersonId.TU: "parles", PersonId.IL: "parle",
        PersonId.ELLE: "parle", PersonId.ON: "parle", PersonId.NOUS: "parlons",
        PersonId.VOUS: "parlez", PersonId.ILS: "parlent", PersonId.ELLES: "parlent",
    }
    for person, form in expected.items():
        result = ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(person))
        assert result.preferred_form == form
        assert result.accepted_forms == (form,)


@pytest.mark.parametrize(
    ("form_id", "person", "expected"),
    [
        (FormId.IMPARFAIT, PersonId.JE, "parlais"),
        (FormId.IMPARFAIT, PersonId.NOUS, "parlions"),
        (FormId.CONDITIONNEL_PRESENT, PersonId.VOUS, "parleriez"),
        (FormId.FUTUR_SIMPLE, PersonId.ILS, "parleront"),
        (FormId.SUBJONCTIF_PRESENT, PersonId.JE, "parle"),
        (FormId.SUBJONCTIF_PRESENT, PersonId.NOUS, "parlions"),
        (FormId.PARTICIPE_PRESENT, None, "parlant"),
        (FormId.GERONDIF_PRESENT, None, "en parlant"),
    ],
)
def test_regular_er_supports_other_simple_and_nonpersonal_forms(form_id, person, expected):
    verb, pattern, construction_id = make_verb()
    ctx = FormContext() if person is None else context(person)
    assert ENGINE.generate(verb, pattern, construction_id, form_id, ctx).preferred_form == expected


@pytest.mark.parametrize(
    ("person", "expected"),
    [(PersonId.TU, "parle"), (PersonId.NOUS, "parlons"), (PersonId.VOUS, "parlez")],
)
def test_regular_er_imperative_only_accepts_tu_nous_vous(person, expected):
    verb, pattern, construction_id = make_verb()
    assert ENGINE.generate(
        verb, pattern, construction_id, FormId.IMPERATIF_PRESENT, context(person)
    ).preferred_form == expected


def test_compound_tense_uses_selected_auxiliary_and_explicit_context():
    verb, pattern, construction_id = make_verb()
    expected = {
        FormId.PASSE_COMPOSE: "ai parlé",
        FormId.PLUS_QUE_PARFAIT: "avais parlé",
        FormId.CONDITIONNEL_PASSE: "aurais parlé",
        FormId.FUTUR_ANTERIEUR: "aurai parlé",
        FormId.SUBJONCTIF_PASSE: "aie parlé",
    }
    masculine_je = context(PersonId.JE, Gender.MASCULINE, GrammaticalNumber.SINGULAR)
    for form_id, answer in expected.items():
        assert ENGINE.generate(verb, pattern, construction_id, form_id, masculine_je).preferred_form == answer


def test_etre_construction_agrees_with_gender_and_number_from_context():
    verb, pattern, construction_id = make_verb("entrer", auxiliary=Auxiliary.ETRE)
    feminine_singular = context(PersonId.JE, Gender.FEMININE, GrammaticalNumber.SINGULAR)
    feminine_plural = context(PersonId.ELLES, Gender.FEMININE, GrammaticalNumber.PLURAL)
    masculine_plural = context(PersonId.ILS, Gender.MASCULINE, GrammaticalNumber.PLURAL)
    assert ENGINE.generate(verb, pattern, construction_id, FormId.PASSE_COMPOSE, feminine_singular).preferred_form == "suis entrée"
    assert ENGINE.generate(verb, pattern, construction_id, FormId.PASSE_COMPOSE, feminine_plural).preferred_form == "sont entrées"
    assert ENGINE.generate(verb, pattern, construction_id, FormId.PASSE_COMPOSE, masculine_plural).preferred_form == "sont entrés"


def test_subject_agreement_is_applied_to_each_approved_generic_participle_variant():
    override = FormOverride(
        form_id=FormId.PARTICIPE_PASSE,
        context=FormContext(),
        preferred_form="entré",
        alternatives=["rentré"],
        operation="add",
        review_status=ReviewStatus.FORMS_REVIEWED,
        source_evidence=[evidence(EvidenceScope.FORM, EvidenceScope.AGREEMENT)],
    )
    verb, pattern, construction_id = make_verb("entrer", auxiliary=Auxiliary.ETRE, overrides=[override])
    feminine_plural = context(PersonId.ELLES, Gender.FEMININE, GrammaticalNumber.PLURAL)
    result = ENGINE.generate(verb, pattern, construction_id, FormId.PASSE_COMPOSE, feminine_plural)
    assert result.accepted_forms == ("sont entrées", "sont rentrées")
    assert result.used_override is True


def test_pronominal_simple_and_imperative_forms_include_reflexive_clitic():
    verb, pattern, construction_id = make_verb(
        "laver", construction_kind=ConstructionKind.PRONOMINAL
    )
    assert ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE)).preferred_form == "me lave"
    assert ENGINE.generate(verb, pattern, construction_id, FormId.IMPERATIF_PRESENT, context(PersonId.TU)).preferred_form == "lave-toi"
    assert ENGINE.generate(verb, pattern, construction_id, FormId.PARTICIPE_PRESENT, FormContext()).preferred_form == "se lavant"
    assert ENGINE.generate(verb, pattern, construction_id, FormId.GERONDIF_PRESENT, FormContext()).preferred_form == "en se lavant"


def test_pronominal_elision_uses_declared_display_infinitive_metadata():
    verb, pattern, construction_id = make_verb(
        "habiller", construction_kind=ConstructionKind.PRONOMINAL, display_infinitive="s'habiller"
    )
    assert ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE)).preferred_form == "m'habille"
    assert ENGINE.generate(verb, pattern, construction_id, FormId.PARTICIPE_PRESENT, FormContext()).preferred_form == "s'habillant"


def test_verb_specific_pronominal_participle_requires_explicit_review_and_can_agree():
    overrides = [
        FormOverride(
            form_id=FormId.PARTICIPE_PASSE,
            context=FormContext(gender=Gender.MASCULINE, number=GrammaticalNumber.SINGULAR),
            preferred_form="lavé",
            review_status=ReviewStatus.FORMS_REVIEWED,
            source_evidence=[evidence(EvidenceScope.FORM, EvidenceScope.AGREEMENT)],
        ),
        FormOverride(
            form_id=FormId.PARTICIPE_PASSE,
            context=FormContext(gender=Gender.FEMININE, number=GrammaticalNumber.SINGULAR),
            preferred_form="lavée",
            review_status=ReviewStatus.FORMS_REVIEWED,
            source_evidence=[evidence(EvidenceScope.FORM, EvidenceScope.AGREEMENT)],
        ),
    ]
    verb, pattern, construction_id = make_verb(
        "laver", construction_kind=ConstructionKind.PRONOMINAL, overrides=overrides
    )
    ctx = context(PersonId.JE, Gender.FEMININE, GrammaticalNumber.SINGULAR)
    assert ENGINE.generate(verb, pattern, construction_id, FormId.PASSE_COMPOSE, ctx).preferred_form == "me suis lavée"

    verb_missing, pattern_missing, construction_missing = make_verb(
        "laver", construction_kind=ConstructionKind.PRONOMINAL
    )
    with pytest.raises(FormNotReviewedError, match="verb-specific participle agreement"):
        ENGINE.generate(
            verb_missing,
            pattern_missing,
            construction_missing,
            FormId.PASSE_COMPOSE,
            context(PersonId.JE, Gender.MASCULINE, GrammaticalNumber.SINGULAR),
        )


def test_form_override_returns_all_reviewed_variants_and_adds_without_losing_base():
    override = FormOverride(
        form_id=FormId.PRESENT_INDICATIF,
        context=FormContext(person=PersonId.JE),
        preferred_form="parle",
        alternatives=["parlo"],
        operation="replace",
        review_status=ReviewStatus.FORMS_REVIEWED,
        source_evidence=[evidence(EvidenceScope.FORM)],
    )
    verb, pattern, construction_id = make_verb(overrides=[override])
    result = ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))
    assert result.preferred_form == "parle"
    assert result.accepted_forms == ("parle", "parlo")
    assert result.used_override is True


def test_add_override_preserves_the_pattern_form_and_adds_reviewed_variant():
    override = FormOverride(
        form_id=FormId.PRESENT_INDICATIF,
        context=FormContext(person=PersonId.JE),
        preferred_form="parle",
        alternatives=["parlo"],
        operation="add",
        review_status=ReviewStatus.FORMS_REVIEWED,
        source_evidence=[evidence(EvidenceScope.FORM)],
    )
    verb, pattern, construction_id = make_verb(overrides=[override])
    result = ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))
    assert result.preferred_form == "parle"
    assert result.accepted_forms == ("parle", "parlo")
    assert result.used_override is True


def test_unreviewed_matching_override_blocks_pattern_fallback():
    override = FormOverride(
        form_id=FormId.PRESENT_INDICATIF,
        context=FormContext(person=PersonId.JE),
        preferred_form="parl-e",
        review_status=ReviewStatus.DRAFT,
    )
    verb, pattern, construction_id = make_verb(overrides=[override])
    with pytest.raises(FormNotReviewedError, match="has a matching override"):
        ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))


def test_unavailable_and_not_reviewed_forms_are_never_generated():
    unavailable = FormAvailability(
        form_id=FormId.PRESENT_INDICATIF,
        context=FormContext(person=PersonId.JE),
        status=AvailabilityStatus.UNAVAILABLE,
        reason="Fixture: unavailable form",
        source_evidence=[evidence(EvidenceScope.AVAILABILITY)],
    )
    verb, pattern, construction_id = make_verb(availability=[unavailable])
    with pytest.raises(FormUnavailableError, match="unavailable form"):
        ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))


def test_defective_verb_requires_explicit_availability_before_algorithmic_generation():
    verb, pattern, construction_id = make_verb("parler", traits=["defective"])
    with pytest.raises(FormNotReviewedError, match="explicit available-form decision"):
        ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))

    available = FormAvailability(
        form_id=FormId.PRESENT_INDICATIF,
        context=FormContext(person=PersonId.JE),
        status=AvailabilityStatus.AVAILABLE,
        reason="Fixture: explicitly reviewed as available",
    )
    verb, pattern, construction_id = make_verb("parler", traits=["defective"], availability=[available])
    assert ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE)).preferred_form == "parle"


def test_unapproved_unknown_or_mismatched_patterns_fail_closed():
    verb, pattern, construction_id = make_verb(review_status=ReviewStatus.DRAFT)
    with pytest.raises(UnapprovedRecordError):
        ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))

    verb, pattern, construction_id = make_verb(algorithm_key="arbitrary_import_path")
    with pytest.raises(UnsupportedPatternError):
        ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))

    verb, pattern, construction_id = make_verb()
    pattern = ConjugationPattern(
        pattern_id=pattern.pattern_id, group_id=pattern.group_id, family_id=pattern.family_id,
        algorithm_key=pattern.algorithm_key, algorithm_version=2,
        review_status=ReviewStatus.APPROVED, source_evidence=pattern.source_evidence,
    )
    with pytest.raises(UnsupportedPatternError, match="does not support version 2"):
        ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))

    verb, pattern, construction_id = make_verb()
    mismatched_pattern = approved_pattern(pattern_id="different_pattern")
    with pytest.raises(PatternMismatchError):
        ENGINE.generate(verb, mismatched_pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))


def test_compound_and_personal_forms_reject_missing_required_context():
    verb, pattern, construction_id = make_verb()
    with pytest.raises(InvalidFormContextError, match="requires a person context"):
        ENGINE.generate(verb, pattern, construction_id, FormId.PRESENT_INDICATIF, FormContext())
    with pytest.raises(InvalidFormContextError, match="requires gender and number context"):
        ENGINE.generate(verb, pattern, construction_id, FormId.PASSE_COMPOSE, context(PersonId.JE))
    with pytest.raises(InvalidFormContextError, match="cannot be requested directly"):
        ENGINE.generate(verb, pattern, construction_id, FormId.PARTICIPE_PASSE, FormContext())


def test_pronominal_compound_form_override_is_returned_as_complete_group():
    override = FormOverride(
        form_id=FormId.PASSE_COMPOSE,
        context=FormContext(
            person=PersonId.JE, gender=Gender.FEMININE, number=GrammaticalNumber.SINGULAR
        ),
        preferred_form="me suis réveillée",
        review_status=ReviewStatus.FORMS_REVIEWED,
        source_evidence=[evidence(EvidenceScope.FORM, EvidenceScope.AGREEMENT)],
    )
    verb, pattern, construction_id = make_verb(
        "laver", construction_kind=ConstructionKind.PRONOMINAL, overrides=[override]
    )
    result = ENGINE.generate(
        verb,
        pattern,
        construction_id,
        FormId.PASSE_COMPOSE,
        context(PersonId.JE, Gender.FEMININE, GrammaticalNumber.SINGULAR),
    )
    assert result.preferred_form == "me suis réveillée"
    assert result.accepted_forms == ("me suis réveillée",)

@pytest.mark.parametrize(
    ("form_id", "person", "expected"),
    [
        (FormId.PRESENT_INDICATIF, PersonId.JE, "fiche"),
        (FormId.PRESENT_INDICATIF, PersonId.NOUS, "fichons"),
        (FormId.IMPARFAIT, PersonId.NOUS, "fichions"),
        (FormId.CONDITIONNEL_PRESENT, PersonId.JE, "ficherais"),
        (FormId.FUTUR_SIMPLE, PersonId.JE, "ficherai"),
        (FormId.SUBJONCTIF_PRESENT, PersonId.JE, "fiche"),
        (FormId.IMPERATIF_PRESENT, PersonId.TU, "fiche"),
        (FormId.PARTICIPE_PRESENT, None, "fichant"),
        (FormId.GERONDIF_PRESENT, None, "en fichant"),
    ],
)
def test_ficher_matches_manually_checked_academie_regular_er_reference_cases(form_id, person, expected):
    """Regression fixture for selected forms on the Académie's regular -ER example.

    This is a synthetic engine test, not a production VerbRecord or an imported
    conjugation dataset. The source is checked manually; no scraping is involved.
    """
    verb, pattern, construction_id = make_verb("ficher")
    ctx = FormContext() if person is None else context(person)
    result = ENGINE.generate(verb, pattern, construction_id, form_id, ctx)
    assert result.preferred_form == expected


def test_ficher_matches_manually_checked_academie_compound_reference_cases():
    verb, pattern, construction_id = make_verb("ficher")
    je_masculine = context(PersonId.JE, Gender.MASCULINE, GrammaticalNumber.SINGULAR)
    nous_masculine_plural = context(PersonId.NOUS, Gender.MASCULINE, GrammaticalNumber.PLURAL)

    assert ENGINE.generate(
        verb, pattern, construction_id, FormId.PASSE_COMPOSE, je_masculine
    ).preferred_form == "ai fiché"
    assert ENGINE.generate(
        verb, pattern, construction_id, FormId.PLUS_QUE_PARFAIT, nous_masculine_plural
    ).preferred_form == "avions fiché"

def test_regular_er_algorithm_requires_matching_registered_family():
    verb, pattern, construction_id = make_verb()
    wrong_family_pattern = ConjugationPattern(
        pattern_id=pattern.pattern_id,
        group_id=pattern.group_id,
        family_id="ger",
        algorithm_key=pattern.algorithm_key,
        algorithm_version=pattern.algorithm_version,
        review_status=ReviewStatus.APPROVED,
        source_evidence=pattern.source_evidence,
    )
    with pytest.raises(PatternMismatchError, match="requires pattern family first_regular"):
        ENGINE.generate(verb, wrong_family_pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))

    verb_without_family, pattern, construction_id = make_verb()
    verb_without_family = VerbRecord(
        verb_id=verb_without_family.verb_id,
        infinitive=verb_without_family.infinitive,
        group_id=verb_without_family.group_id,
        family_ids=[],
        pattern_id=verb_without_family.pattern_id,
        regularity=verb_without_family.regularity,
        traits=verb_without_family.traits,
        review_status=verb_without_family.review_status,
        default_construction_id=verb_without_family.default_construction_id,
        constructions=verb_without_family.constructions,
        source_evidence=verb_without_family.source_evidence,
    )
    with pytest.raises(PatternMismatchError, match="do not include the registered pattern family"):
        ENGINE.generate(verb_without_family, pattern, construction_id, FormId.PRESENT_INDICATIF, context(PersonId.JE))
