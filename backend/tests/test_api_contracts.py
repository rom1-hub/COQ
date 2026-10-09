from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.contracts import (
    ApiErrorCode,
    ApiErrorResponse,
    ExerciseAnswerRequest,
    ExerciseAnswerResponse,
    ExerciseCreateRequest,
    ExerciseQuestionResponse,
    ExerciseSessionResponse,
    ConjugationRowResponse,
    ConjugationTableResponse,
    ScopeListResponse,
    ScopeResponse,
    VerbProfileResponse,
)
from app.domain.verb_contracts import (
    ConstructionKind, FormContext, FormId, PersonId, ReviewStatus, ScopeKind, ScopeStatus, VerbGroup,
)


SELECTABLE_FORMS = [
    FormId.PRESENT_INDICATIF,
    FormId.IMPERATIF_PRESENT,
    FormId.IMPARFAIT,
    FormId.CONDITIONNEL_PRESENT,
    FormId.FUTUR_SIMPLE,
    FormId.SUBJONCTIF_PRESENT,
    FormId.PASSE_COMPOSE,
    FormId.PLUS_QUE_PARFAIT,
    FormId.CONDITIONNEL_PASSE,
    FormId.FUTUR_ANTERIEUR,
    FormId.SUBJONCTIF_PASSE,
    FormId.PARTICIPE_PRESENT,
    FormId.GERONDIF_PRESENT,
]


def test_exercise_request_requires_one_selector_and_only_selectable_forms():
    request = ExerciseCreateRequest(scope_id="group:1", form_ids=[FormId.PRESENT_INDICATIF])
    assert request.question_count == 20

    with pytest.raises(ValidationError, match="provide exactly one of verb_id or scope_id"):
        ExerciseCreateRequest(form_ids=[FormId.PRESENT_INDICATIF])
    with pytest.raises(ValidationError, match="provide exactly one of verb_id or scope_id"):
        ExerciseCreateRequest(verb_id="v_parler", scope_id="group:1", form_ids=[FormId.PRESENT_INDICATIF])
    with pytest.raises(ValidationError, match="cannot be selected directly"):
        ExerciseCreateRequest(verb_id="v_parler", form_ids=[FormId.PARTICIPE_PASSE])


def test_exercise_request_can_target_a_verb_and_multiple_forms_without_duplicate_ids():
    request = ExerciseCreateRequest(
        verb_id="v_parler",
        construction_id="parler.non_pronominal",
        form_ids=[FormId.PRESENT_INDICATIF, FormId.GERONDIF_PRESENT],
        question_count=20,
    )
    assert request.verb_id == "v_parler"
    with pytest.raises(ValidationError, match="form_ids must be unique"):
        ExerciseCreateRequest(
            scope_id="group:1",
            form_ids=[FormId.PRESENT_INDICATIF, FormId.PRESENT_INDICATIF],
        )


def test_question_response_does_not_leak_correct_answers_before_submission():
    question = ExerciseQuestionResponse(
        question_id=uuid4(),
        verb_id="v_parler",
        infinitive="parler",
        construction_id="parler.non_pronominal",
        form_id=FormId.PRESENT_INDICATIF,
        person=PersonId.JE,
        context=FormContext(person=PersonId.JE),
        prompt="parler · Présent de l'indicatif · je",
        instruction="Escribe la forma conjugada.",
    )
    serialized = question.model_dump()
    assert "preferred_answer" not in serialized
    assert "accepted_answers" not in serialized
    assert "correct_answer" not in serialized


def test_exercise_session_checks_question_count_and_unique_question_ids():
    question = ExerciseQuestionResponse(
        question_id=uuid4(),
        verb_id="v_parler",
        infinitive="parler",
        construction_id="parler.non_pronominal",
        form_id=FormId.PRESENT_INDICATIF,
        person=PersonId.JE,
        context=FormContext(person=PersonId.JE),
        prompt="parler · Présent de l'indicatif · je",
        instruction="Escribe la forma conjugada.",
    )
    session = ExerciseSessionResponse(session_id=uuid4(), question_count=1, questions=[question])
    assert session.question_count == 1
    with pytest.raises(ValidationError, match="question_count must equal"):
        ExerciseSessionResponse(session_id=uuid4(), question_count=2, questions=[question])


def test_answer_contract_normalizes_nothing_it_should_not_normalize():
    answer = ExerciseAnswerRequest(question_id=uuid4(), answer="  achète  ")
    assert answer.answer == "achète"
    feedback = ExerciseAnswerResponse(
        question_id=answer.question_id,
        is_correct=True,
        preferred_answer="achète",
        accepted_answers=["achète"],
        attempt_count=1,
    )
    assert feedback.preferred_answer == "achète"


def test_api_errors_use_stable_codes_not_exception_text():
    response = ApiErrorResponse(
        code=ApiErrorCode.FORM_NOT_AVAILABLE,
        message="La forme demandée no está disponible para este verbo.",
        details={"form_id": "subjonctif_passe"},
    )
    assert response.code == ApiErrorCode.FORM_NOT_AVAILABLE
    assert response.details["form_id"] == "subjonctif_passe"


def test_empty_ui_scope_maps_to_a_stable_all_approved_scope_id():
    request = ExerciseCreateRequest(
        scope_id="all:approved_verbs",
        form_ids=[FormId.PRESENT_INDICATIF],
        question_count=20,
    )
    assert request.scope_id == "all:approved_verbs"
    scope = ScopeResponse(
        scope_id="all:approved_verbs",
        label_es="Todos los grupos y familias",
        kind=ScopeKind.ALL,
        status=ScopeStatus.PLANNED,
        display_order=0,
    )
    assert scope.kind == ScopeKind.ALL
    assert scope.status == ScopeStatus.PLANNED


def test_verb_specific_practice_does_not_accept_filters_that_should_be_locked():
    with pytest.raises(ValidationError, match="filters are derived from the selected verb profile"):
        ExerciseCreateRequest(
            verb_id="v_parler",
            form_ids=[FormId.PRESENT_INDICATIF],
            auxiliary="etre",
        )
    with pytest.raises(ValidationError, match="construction_id is only valid when targeting a specific verb"):
        ExerciseCreateRequest(
            scope_id="group:1",
            construction_id="parler.non_pronominal",
            form_ids=[FormId.PRESENT_INDICATIF],
        )


def test_public_verb_profile_cannot_claim_candidate_is_approved_by_default():
    with pytest.raises(ValidationError, match="Field required"):
        VerbProfileResponse(
            verb_id="v_parler",
            infinitive="parler",
            group_id=VerbGroup.FIRST,
            family_ids=["first_regular"],
            pattern_id="first_er_regular",
            default_construction_id="parler.non_pronominal",
            constructions=[],
            selectable_form_ids=[FormId.PRESENT_INDICATIF],
        )

    with pytest.raises(ValidationError, match="public verb profiles must be approved"):
        VerbProfileResponse(
            verb_id="v_parler",
            infinitive="parler",
            group_id=VerbGroup.FIRST,
            family_ids=["first_regular"],
            pattern_id="first_er_regular",
            default_construction_id="parler.non_pronominal",
            constructions=[{
                "construction_id": "parler.non_pronominal",
                "kind": ConstructionKind.NON_PRONOMINAL,
                "display_infinitive": "parler",
                "auxiliary": "avoir",
                "review_status": ReviewStatus.CANDIDATE,
            }],
            selectable_form_ids=[FormId.PRESENT_INDICATIF],
            review_status=ReviewStatus.CANDIDATE,
        )


def test_compound_table_and_question_require_gender_number_context():
    with pytest.raises(ValidationError, match="compound-form rows require gender/number context"):
        ConjugationTableResponse(
            form_id=FormId.PASSE_COMPOSE,
            label_fr="Passé composé",
            rows=[ConjugationRowResponse(
                person=PersonId.JE,
                context=FormContext(person=PersonId.JE),
                display_subject="je (masculin singulier)",
                display_forms=["ai parlé"],
            )],
        )
    with pytest.raises(ValidationError, match="compound-form questions require gender/number context"):
        ExerciseQuestionResponse(
            question_id=uuid4(),
            verb_id="v_parler",
            infinitive="parler",
            construction_id="parler.non_pronominal",
            form_id=FormId.PASSE_COMPOSE,
            person=PersonId.JE,
            context=FormContext(person=PersonId.JE),
            prompt="parler · Passé composé · je (masculin singulier)",
            instruction="Escribe el grupo verbal conjugado.",
        )


def test_public_scope_list_cannot_include_planned_selectors():
    planned = ScopeResponse(
        scope_id="collection:common_100",
        label_es="100 verbos más comunes",
        kind=ScopeKind.COLLECTION,
        status=ScopeStatus.PLANNED,
        display_order=16,
    )
    with pytest.raises(ValidationError, match="only return active scopes"):
        ScopeListResponse(scopes=[planned])
