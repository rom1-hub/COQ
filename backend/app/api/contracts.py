"""Versioned request/response schemas for the future COQ conjugation API.

Only the health endpoint is currently implemented; these models define the API
shape without pretending that the conjugation engine or exercise service exists.
"""
from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.domain.verb_contracts import (
    Auxiliary,
    ConstructionKind,
    COMPOUND_FORMS,
    FormContext,
    FormId,
    GrammaticalNumber,
    NON_PERSONAL_FORMS,
    PERSONAL_FORMS,
    PersonId,
    ReviewStatus,
    ScopeKind,
    ScopeStatus,
    VerbGroup,
)


SELECTABLE_FORM_IDS = {
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
}


class ApiContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ApiErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    VERB_NOT_FOUND = "VERB_NOT_FOUND"
    VERB_NOT_APPROVED = "VERB_NOT_APPROVED"
    CONSTRUCTION_NOT_AVAILABLE = "CONSTRUCTION_NOT_AVAILABLE"
    FORM_NOT_AVAILABLE = "FORM_NOT_AVAILABLE"
    SCOPE_NOT_ACTIVE = "SCOPE_NOT_ACTIVE"
    INSUFFICIENT_QUESTIONS = "INSUFFICIENT_QUESTIONS"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    QUESTION_NOT_IN_SESSION = "QUESTION_NOT_IN_SESSION"


class ApiErrorResponse(ApiContractModel):
    code: ApiErrorCode
    message: str = Field(min_length=1, max_length=500)
    details: dict[str, str] = Field(default_factory=dict, max_length=20)


class VerbSearchItem(ApiContractModel):
    verb_id: str
    infinitive: str
    label: str
    group_id: VerbGroup
    family_ids: list[str]
    default_construction_id: str


class VerbSearchResponse(ApiContractModel):
    items: list[VerbSearchItem] = Field(max_length=50)
    query: str = Field(min_length=1, max_length=100)
    limit: int = Field(ge=1, le=50)

    @model_validator(mode="after")
    def results_fit_requested_limit(self) -> "VerbSearchResponse":
        if len(self.items) > self.limit:
            raise ValueError("search results cannot exceed the requested limit")
        return self


class ConstructionSummary(ApiContractModel):
    construction_id: str
    kind: ConstructionKind
    display_infinitive: str
    auxiliary: Auxiliary
    review_status: ReviewStatus


class VerbProfileResponse(ApiContractModel):
    verb_id: str = Field(pattern=r"^v_[a-z0-9]+(?:_[a-z0-9]+)*$")
    infinitive: str
    group_id: VerbGroup
    family_ids: list[str]
    pattern_id: str
    default_construction_id: str
    constructions: list[ConstructionSummary]
    selectable_form_ids: list[FormId]
    review_status: ReviewStatus
    practice_filters_are_catalog_driven: bool = True

    @model_validator(mode="after")
    def only_approved_profiles_are_public(self) -> "VerbProfileResponse":
        if self.review_status != ReviewStatus.APPROVED:
            raise ValueError("public verb profiles must be approved")
        if not self.selectable_form_ids:
            raise ValueError("approved profiles must expose at least one selectable form")
        if any(form not in SELECTABLE_FORM_IDS for form in self.selectable_form_ids):
            raise ValueError("profile form IDs must be selectable UI forms")
        construction_ids = [construction.construction_id for construction in self.constructions]
        if self.default_construction_id not in construction_ids:
            raise ValueError("default construction must exist in the returned profile")
        if any(construction.review_status != ReviewStatus.APPROVED for construction in self.constructions):
            raise ValueError("public verb profiles may contain only approved constructions")
        if len(construction_ids) != len(set(construction_ids)):
            raise ValueError("construction IDs in a profile must be unique")
        if len(self.selectable_form_ids) != len(set(self.selectable_form_ids)):
            raise ValueError("selectable form IDs in a profile must be unique")
        return self


class ConjugationRowResponse(ApiContractModel):
    person: PersonId | None = None
    context: FormContext = Field(default_factory=FormContext)
    display_subject: str | None = None
    display_forms: list[str] = Field(min_length=1)


class ConjugationTableResponse(ApiContractModel):
    form_id: FormId
    label_fr: str
    rows: list[ConjugationRowResponse] = Field(min_length=1, max_length=18)

    @model_validator(mode="after")
    def validate_rows_match_form(self) -> "ConjugationTableResponse":
        if self.form_id not in SELECTABLE_FORM_IDS:
            raise ValueError("internal-only forms cannot be exposed in conjugation tables")
        for row in self.rows:
            if self.form_id in PERSONAL_FORMS:
                if row.person is None or row.context.person != row.person:
                    raise ValueError("personal-form rows require matching person and context.person")
                if self.form_id == FormId.IMPERATIF_PRESENT and row.person not in {PersonId.TU, PersonId.NOUS, PersonId.VOUS}:
                    raise ValueError("imperative rows only allow tu, nous or vous")
                if self.form_id in COMPOUND_FORMS and (row.context.gender is None or row.context.number is None):
                    raise ValueError("compound-form rows require gender/number context")
                if self.form_id not in COMPOUND_FORMS and (row.context.gender is not None or row.context.number is not None):
                    raise ValueError("simple-form rows cannot use gender/number context")
            elif row.person is not None or row.context.person is not None:
                raise ValueError("non-personal-form rows cannot have a person")
            if self.form_id in {FormId.PARTICIPE_PRESENT, FormId.GERONDIF_PRESENT} and (row.context.gender is not None or row.context.number is not None):
                raise ValueError("participe présent and gérondif rows cannot have agreement context")
        if self.form_id in PERSONAL_FORMS:
            if self.form_id in COMPOUND_FORMS:
                keys = [(row.person, row.context.gender, row.context.number, row.context.usage) for row in self.rows]
                if len(keys) != len(set(keys)):
                    raise ValueError("conjugation table contains duplicate person/context rows")
            else:
                persons = [row.person for row in self.rows]
                if len(persons) != len(set(persons)):
                    raise ValueError("simple-form tables cannot duplicate a subject row")
        return self


class ConjugationLookupResponse(ApiContractModel):
    verb_id: str
    infinitive: str
    construction_id: str
    tables: list[ConjugationTableResponse] = Field(min_length=1, max_length=13)
    source_urls: list[HttpUrl] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_lookup_tables(self) -> "ConjugationLookupResponse":
        form_ids = [table.form_id for table in self.tables]
        if len(form_ids) != len(set(form_ids)):
            raise ValueError("conjugation lookup cannot contain duplicate form tables")
        if any(form_id not in SELECTABLE_FORM_IDS for form_id in form_ids):
            raise ValueError("conjugation lookup cannot expose internal-only forms")
        return self


class ExerciseCreateRequest(ApiContractModel):
    verb_id: str | None = Field(default=None, pattern=r"^v_[a-z0-9]+(?:_[a-z0-9]+)*$")
    scope_id: str | None = Field(default=None, pattern=r"^(all|group|family|collection):[a-z0-9_]+$")
    construction_id: str | None = None
    # These are filters only; when a verb is chosen, the server derives them from its profile.
    construction: ConstructionKind | None = None
    auxiliary: Auxiliary | None = None
    form_ids: list[FormId] = Field(min_length=1, max_length=13)
    question_count: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_selection(self) -> "ExerciseCreateRequest":
        if bool(self.verb_id) == bool(self.scope_id):
            raise ValueError("provide exactly one of verb_id or scope_id")
        if len(self.form_ids) != len(set(self.form_ids)):
            raise ValueError("form_ids must be unique")
        if any(form not in SELECTABLE_FORM_IDS for form in self.form_ids):
            raise ValueError("participe_passe is an internal base form and cannot be selected directly")
        if self.construction_id and not self.verb_id:
            raise ValueError("construction_id is only valid when targeting a specific verb")
        if self.verb_id and self.scope_id:
            raise ValueError("a verb-specific session derives scope/group/family from the verb profile")
        if self.verb_id and (self.construction is not None or self.auxiliary is not None):
            raise ValueError("construction and auxiliary filters are derived from the selected verb profile")
        if self.scope_id and self.construction_id:
            raise ValueError("construction_id is only valid when targeting a specific verb")
        return self


class ExerciseQuestionResponse(ApiContractModel):
    question_id: UUID
    verb_id: str = Field(pattern=r"^v_[a-z0-9]+(?:_[a-z0-9]+)*$")
    infinitive: str
    construction_id: str
    form_id: FormId
    person: PersonId | None = None
    context: FormContext = Field(default_factory=FormContext)
    prompt: str = Field(min_length=1, max_length=300)
    instruction: str = Field(min_length=1, max_length=300)
    # Correct/accepted answers must never be included in this response.

    @model_validator(mode="after")
    def validate_question_context(self) -> "ExerciseQuestionResponse":
        if self.form_id not in SELECTABLE_FORM_IDS:
            raise ValueError("exercise questions cannot use internal-only forms")
        if self.form_id in PERSONAL_FORMS:
            if self.person is None or self.context.person != self.person:
                raise ValueError("personal-form questions require matching person and context.person")
            if self.form_id == FormId.IMPERATIF_PRESENT and self.person not in {PersonId.TU, PersonId.NOUS, PersonId.VOUS}:
                raise ValueError("imperative questions only allow tu, nous or vous")
            if self.form_id in COMPOUND_FORMS and (self.context.gender is None or self.context.number is None):
                raise ValueError("compound-form questions require gender/number context")
            if self.form_id not in COMPOUND_FORMS and (self.context.gender is not None or self.context.number is not None):
                raise ValueError("simple-form questions cannot use gender/number context")
        elif self.person is not None or self.context.person is not None:
            raise ValueError("non-personal-form questions cannot have a person")
        if self.form_id in {FormId.PARTICIPE_PRESENT, FormId.GERONDIF_PRESENT} and (self.context.gender is not None or self.context.number is not None):
            raise ValueError("participe présent and gérondif questions cannot have agreement context")
        return self


class ExerciseSessionResponse(ApiContractModel):
    session_id: UUID
    question_count: int = Field(ge=1, le=100)
    questions: list[ExerciseQuestionResponse] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_question_count(self) -> "ExerciseSessionResponse":
        if self.question_count != len(self.questions):
            raise ValueError("question_count must equal len(questions)")
        ids = [item.question_id for item in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("question_id values must be unique within a session")
        return self


class ExerciseAnswerRequest(ApiContractModel):
    question_id: UUID
    answer: str = Field(min_length=1, max_length=200)


class ExerciseAnswerResponse(ApiContractModel):
    question_id: UUID
    is_correct: bool
    preferred_answer: str = Field(min_length=1, max_length=200)
    accepted_answers: list[str] = Field(min_length=1, max_length=10)
    attempt_count: int = Field(ge=1)
    # Returned only after an answer is submitted, never with the initial questions.

    @model_validator(mode="after")
    def preferred_answer_must_be_accepted(self) -> "ExerciseAnswerResponse":
        if self.preferred_answer not in self.accepted_answers:
            raise ValueError("preferred_answer must be included in accepted_answers")
        if len(self.accepted_answers) != len(set(self.accepted_answers)):
            raise ValueError("accepted_answers must not contain duplicates")
        return self


class ScopeResponse(ApiContractModel):
    scope_id: str = Field(pattern=r"^(all|group|family|collection):[a-z0-9_]+$")
    label_es: str
    label_fr: str | None = None
    kind: ScopeKind
    group_id: VerbGroup | None = None
    status: ScopeStatus
    display_order: int = Field(ge=0)


class ScopeListResponse(ApiContractModel):
    scopes: list[ScopeResponse] = Field(max_length=200)

    @model_validator(mode="after")
    def only_active_scopes_are_public(self) -> "ScopeListResponse":
        if any(scope.status != ScopeStatus.ACTIVE for scope in self.scopes):
            raise ValueError("catalog scope endpoint may only return active scopes")
        scope_ids = [scope.scope_id for scope in self.scopes]
        if len(scope_ids) != len(set(scope_ids)):
            raise ValueError("scope IDs must be unique")
        order_values = [scope.display_order for scope in self.scopes]
        if len(order_values) != len(set(order_values)):
            raise ValueError("scope display_order values must be unique")
        return self


class ContractValidationSummary(ApiContractModel):
    schema_version: str = "1.0"
    valid: bool
    record_count: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list, max_length=100)
