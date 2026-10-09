"""Typed, versioned data contracts for the COQ French verb catalogue.

These models validate catalogue records. They deliberately do not conjugate verbs.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class VerbGroup(str, Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"


class ConstructionKind(str, Enum):
    NON_PRONOMINAL = "non_pronominal"
    PRONOMINAL = "pronominal"


class Auxiliary(str, Enum):
    AVOIR = "avoir"
    ETRE = "etre"


class ParticipleAgreementPolicy(str, Enum):
    INVARIABLE = "invariable"
    SUBJECT = "subject"
    VERB_SPECIFIC = "verb_specific"


class Regularity(str, Enum):
    REGULAR = "regular"
    ORTHOGRAPHIC_ALTERNATION = "orthographic_alternation"
    IRREGULAR = "irregular"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    METADATA_REVIEWED = "metadata_reviewed"
    FORMS_REVIEWED = "forms_reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class EvidenceMethod(str, Enum):
    MANUAL_REFERENCE_CHECK = "manual_reference_check"
    LICENSED_DATASET = "licensed_dataset"
    LINGUISTIC_OWNER_APPROVAL = "linguistic_owner_approval"
    COQ_RULE_REVIEW = "coq_rule_review"


class EvidenceScope(str, Enum):
    LEMMA = "lemma"
    GROUP = "group"
    FAMILY = "family"
    PATTERN = "pattern"
    CONSTRUCTION = "construction"
    AUXILIARY = "auxiliary"
    AGREEMENT = "agreement"
    FORM = "form"
    AVAILABILITY = "availability"
    DATA_LICENSE = "data_license"


class FormId(str, Enum):
    PRESENT_INDICATIF = "present_indicatif"
    IMPERATIF_PRESENT = "imperatif_present"
    IMPARFAIT = "imparfait"
    CONDITIONNEL_PRESENT = "conditionnel_present"
    FUTUR_SIMPLE = "futur_simple"
    SUBJONCTIF_PRESENT = "subjonctif_present"
    PASSE_COMPOSE = "passe_compose"
    PLUS_QUE_PARFAIT = "plus_que_parfait"
    CONDITIONNEL_PASSE = "conditionnel_passe"
    FUTUR_ANTERIEUR = "futur_anterieur"
    SUBJONCTIF_PASSE = "subjonctif_passe"
    PARTICIPE_PRESENT = "participe_present"
    GERONDIF_PRESENT = "gerondif_present"
    # Internal base form used to assemble compound tenses; not a selectable UI option.
    PARTICIPE_PASSE = "participe_passe"


class PersonId(str, Enum):
    JE = "je"
    TU = "tu"
    IL = "il"
    ELLE = "elle"
    ON = "on"
    NOUS = "nous"
    VOUS = "vous"
    ILS = "ils"
    ELLES = "elles"


class Gender(str, Enum):
    MASCULINE = "masculine"
    FEMININE = "feminine"


class GrammaticalNumber(str, Enum):
    SINGULAR = "singular"
    PLURAL = "plural"


class Usage(str, Enum):
    STANDARD = "standard"
    COURTESY = "courtesy"


class AvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_REVIEWED = "not_reviewed"


PERSONAL_FORMS = {
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
}
COMPOUND_FORMS = {
    FormId.PASSE_COMPOSE,
    FormId.PLUS_QUE_PARFAIT,
    FormId.CONDITIONNEL_PASSE,
    FormId.FUTUR_ANTERIEUR,
    FormId.SUBJONCTIF_PASSE,
}

# Authoritative structural recipe for the five COQ compound tenses.
# The selected construction supplies the one permitted auxiliary (avoir/être).
COMPOUND_AUXILIARY_TENSE: dict[FormId, FormId] = {
    FormId.PASSE_COMPOSE: FormId.PRESENT_INDICATIF,
    FormId.PLUS_QUE_PARFAIT: FormId.IMPARFAIT,
    FormId.CONDITIONNEL_PASSE: FormId.CONDITIONNEL_PRESENT,
    FormId.FUTUR_ANTERIEUR: FormId.FUTUR_SIMPLE,
    FormId.SUBJONCTIF_PASSE: FormId.SUBJONCTIF_PRESENT,
}
NON_PERSONAL_FORMS = {
    FormId.PARTICIPE_PRESENT,
    FormId.GERONDIF_PRESENT,
    FormId.PARTICIPE_PASSE,
}


class SourceEvidence(ContractModel):
    """Evidence that can be audited later; automated scraping is not a method."""

    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    authority: str = Field(min_length=2, max_length=100)
    label: str = Field(min_length=2, max_length=250)
    url: HttpUrl | None = None
    method: EvidenceMethod
    scopes: list[EvidenceScope] = Field(min_length=1)
    consulted_on: date | None = None
    edition: str | None = Field(default=None, max_length=100)
    dataset_version: str | None = Field(default=None, max_length=100)
    license_name: str | None = Field(default=None, max_length=150)
    license_url: HttpUrl | None = None
    decision_id: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_evidence_provenance(self) -> "SourceEvidence":
        if self.method == EvidenceMethod.LICENSED_DATASET:
            if not self.url or not self.license_name or not self.license_url:
                raise ValueError("licensed_dataset evidence requires url, license_name and license_url")
            if not self.dataset_version:
                raise ValueError("licensed_dataset evidence requires dataset_version or commit")
        if self.method == EvidenceMethod.MANUAL_REFERENCE_CHECK:
            if not self.url:
                raise ValueError("manual reference checks require a source url")
            if self.consulted_on is None:
                raise ValueError("manual reference checks require consulted_on")
        if self.method in {EvidenceMethod.LINGUISTIC_OWNER_APPROVAL, EvidenceMethod.COQ_RULE_REVIEW}:
            if not self.decision_id:
                raise ValueError("internal linguistic reviews require a decision_id")
        return self


class FormContext(ContractModel):
    """Optional agreement context for a form whose surface spelling varies."""

    person: PersonId | None = None
    gender: Gender | None = None
    number: GrammaticalNumber | None = None
    usage: Usage | None = None

    @model_validator(mode="after")
    def validate_context(self) -> "FormContext":
        if (self.gender is None) != (self.number is None):
            raise ValueError("gender and number must be provided together")

        if self.person == PersonId.VOUS:
            if self.usage == Usage.COURTESY and self.number != GrammaticalNumber.SINGULAR:
                raise ValueError("courtesy usage is reserved for singular vous")
            if self.number == GrammaticalNumber.SINGULAR and self.usage != Usage.COURTESY:
                raise ValueError("singular vous requires courtesy usage")
        elif self.usage == Usage.COURTESY:
            raise ValueError("courtesy usage is reserved for vous")

        if self.number is not None:
            fixed_singular = {PersonId.JE, PersonId.TU, PersonId.IL, PersonId.ELLE}
            fixed_plural = {PersonId.NOUS, PersonId.ILS, PersonId.ELLES}
            if self.person in fixed_singular and self.number != GrammaticalNumber.SINGULAR:
                raise ValueError(f"{self.person.value} requires singular agreement context")
            if self.person in fixed_plural and self.number != GrammaticalNumber.PLURAL:
                raise ValueError(f"{self.person.value} requires plural agreement context")

        if self.person == PersonId.ON:
            if self.gender == Gender.FEMININE and self.number == GrammaticalNumber.SINGULAR:
                raise ValueError("COQ does not offer feminine-singular agreement context for on")
        if self.person in {PersonId.IL, PersonId.ILS} and self.gender == Gender.FEMININE:
            raise ValueError("il/ils cannot use feminine agreement context")
        if self.person in {PersonId.ELLE, PersonId.ELLES} and self.gender == Gender.MASCULINE:
            raise ValueError("elle/elles cannot use masculine agreement context")
        return self


class FormOverride(ContractModel):
    """A reviewed exact form override; listed variants are all valid alternatives."""

    form_id: FormId
    context: FormContext = Field(default_factory=FormContext)
    preferred_form: str = Field(min_length=1, max_length=100)
    alternatives: list[str] = Field(default_factory=list, max_length=10)
    operation: Literal["replace", "add"] = "replace"
    review_status: ReviewStatus = ReviewStatus.DRAFT
    source_evidence: list[SourceEvidence] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_form_context_and_review(self) -> "FormOverride":
        person = self.context.person
        if self.form_id in PERSONAL_FORMS and person is None:
            raise ValueError(f"{self.form_id.value} requires a person context")
        if self.form_id in NON_PERSONAL_FORMS and person is not None:
            raise ValueError(f"{self.form_id.value} does not take a person context")
        if self.form_id == FormId.IMPERATIF_PRESENT and person not in {
            PersonId.TU,
            PersonId.NOUS,
            PersonId.VOUS,
        }:
            raise ValueError("imperatif_present only accepts tu, nous or vous")
        has_agreement_context = self.context.gender is not None
        if has_agreement_context and self.form_id not in COMPOUND_FORMS | {FormId.PARTICIPE_PASSE}:
            raise ValueError("gender/number context is only valid for compound forms or participe_passe")
        if self.form_id in COMPOUND_FORMS and not has_agreement_context:
            raise ValueError("compound forms require an explicit gender/number agreement context")
        if self.form_id in {FormId.PARTICIPE_PRESENT, FormId.GERONDIF_PRESENT} and has_agreement_context:
            raise ValueError("participe présent and gérondif présent do not take agreement context")
        forms = [self.preferred_form, *self.alternatives]
        normalized = [form.strip() for form in forms]
        if any(not form for form in normalized):
            raise ValueError("forms cannot be empty or whitespace")
        if len(set(normalized)) != len(normalized):
            raise ValueError("preferred form and alternatives must be unique")
        if self.review_status in {ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED} and not self.source_evidence:
            raise ValueError("reviewed form overrides require source evidence")
        return self

    @property
    def accepted_forms(self) -> tuple[str, ...]:
        return (self.preferred_form, *self.alternatives)


class FormAvailability(ContractModel):
    """Explicit availability exceptions, essential for defective/impersonal verbs."""

    form_id: FormId
    context: FormContext = Field(default_factory=FormContext)
    status: AvailabilityStatus
    reason: str = Field(min_length=2, max_length=500)
    source_evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_availability_context(self) -> "FormAvailability":
        person = self.context.person
        has_agreement_context = self.context.gender is not None
        if self.form_id in PERSONAL_FORMS and person is None:
            # A person-less rule marks the availability of the entire tense/form.
            if self.status == AvailabilityStatus.AVAILABLE:
                raise ValueError("an availability override cannot declare a whole personal form available")
            if has_agreement_context:
                raise ValueError("a whole-form availability override cannot have agreement context")
        if self.form_id in PERSONAL_FORMS and person is not None:
            if self.form_id in COMPOUND_FORMS and not has_agreement_context:
                raise ValueError("compound-form availability requires gender/number context when person-specific")
            if self.form_id not in COMPOUND_FORMS and has_agreement_context:
                raise ValueError("simple-form availability cannot have gender/number context")
        if self.form_id in NON_PERSONAL_FORMS and person is not None:
            raise ValueError("non-personal availability does not take a person context")
        if self.form_id in {FormId.PARTICIPE_PRESENT, FormId.GERONDIF_PRESENT} and has_agreement_context:
            raise ValueError("participe présent and gérondif présent do not take agreement context")
        if self.status == AvailabilityStatus.UNAVAILABLE and not self.source_evidence:
            raise ValueError("unavailable forms require supporting source evidence")
        return self


class ConstructionProfile(ContractModel):
    """A specific non-pronominal or pronominal construction for one lemma."""

    construction_id: str = Field(pattern=r"^[a-z0-9]+(?:[._:-][a-z0-9]+)*$")
    kind: ConstructionKind
    display_infinitive: str = Field(min_length=2, max_length=100)
    auxiliary: Auxiliary
    participle_agreement: ParticipleAgreementPolicy
    review_status: ReviewStatus = ReviewStatus.DRAFT
    form_overrides: list[FormOverride] = Field(default_factory=list)
    availability_overrides: list[FormAvailability] = Field(default_factory=list)
    source_evidence: list[SourceEvidence] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_construction_rules(self) -> "ConstructionProfile":
        expected_policy = {
            (ConstructionKind.NON_PRONOMINAL, Auxiliary.AVOIR): ParticipleAgreementPolicy.INVARIABLE,
            (ConstructionKind.NON_PRONOMINAL, Auxiliary.ETRE): ParticipleAgreementPolicy.SUBJECT,
            (ConstructionKind.PRONOMINAL, Auxiliary.ETRE): ParticipleAgreementPolicy.VERB_SPECIFIC,
        }.get((self.kind, self.auxiliary))
        if expected_policy is None:
            raise ValueError("COQ construction policy does not allow pronominal construction with avoir")
        if self.participle_agreement != expected_policy:
            raise ValueError(
                f"{self.kind.value} + {self.auxiliary.value} requires participle_agreement={expected_policy.value}"
            )
        if self.review_status in {ReviewStatus.METADATA_REVIEWED, ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED} and not self.source_evidence:
            raise ValueError("reviewed construction profiles require source evidence")
        override_keys = [
            (item.form_id, item.context.person, item.context.gender, item.context.number, item.context.usage)
            for item in self.form_overrides
        ]
        if len(override_keys) != len(set(override_keys)):
            raise ValueError("duplicate form override for the same form/context")
        availability_keys = [
            (item.form_id, item.context.person, item.context.gender, item.context.number, item.context.usage)
            for item in self.availability_overrides
        ]
        if len(availability_keys) != len(set(availability_keys)):
            raise ValueError("duplicate availability override for the same form/context")
        return self


class VerbRecord(ContractModel):
    """Canonical source record for one French infinitive/lemma."""

    schema_version: Literal["1.0"] = "1.0"
    verb_id: str = Field(pattern=r"^v_[a-z0-9]+(?:_[a-z0-9]+)*$")
    infinitive: str = Field(min_length=2, max_length=100)
    search_aliases: list[str] = Field(default_factory=list, max_length=20)
    group_id: VerbGroup | None = None
    family_ids: list[str] = Field(default_factory=list, max_length=10)
    pattern_id: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:[._:-][a-z0-9]+)*$")
    regularity: Regularity
    traits: list[Literal["impersonal", "defective"]] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.DRAFT
    default_construction_id: str
    constructions: list[ConstructionProfile] = Field(min_length=1)
    source_evidence: list[SourceEvidence] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_verb_record(self) -> "VerbRecord":
        infinitive = self.infinitive.strip()
        if infinitive != infinitive.lower():
            raise ValueError("infinitive must be stored in lowercase; presentation casing belongs to the UI")
        if infinitive.startswith(("se ", "s'", "s’")):
            raise ValueError("store the base infinitive here; pronominal surface forms belong to constructions")
        if len(set(self.search_aliases)) != len(self.search_aliases):
            raise ValueError("search_aliases must be unique")
        construction_ids = [construction.construction_id for construction in self.constructions]
        if len(construction_ids) != len(set(construction_ids)):
            raise ValueError("construction_ids must be unique within a verb record")
        if self.default_construction_id not in construction_ids:
            raise ValueError("default_construction_id must reference an included construction")
        if self.review_status in {ReviewStatus.METADATA_REVIEWED, ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED}:
            if not self.source_evidence:
                raise ValueError("reviewed verbs require source evidence")
            if self.group_id is None:
                raise ValueError("reviewed verbs require an audited group")
        if self.review_status in {ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED} and self.pattern_id is None:
            raise ValueError("forms-reviewed verbs require a registered pattern")
        if self.review_status == ReviewStatus.APPROVED:
            if any(item.review_status != ReviewStatus.APPROVED for item in self.constructions):
                raise ValueError("approved verbs may only contain approved construction profiles")
        return self

    @property
    def is_approved_for_practice(self) -> bool:
        """Whether production exercise generation may use this record."""
        return (
            self.review_status == ReviewStatus.APPROVED
            and any(
                item.construction_id == self.default_construction_id
                and item.review_status == ReviewStatus.APPROVED
                for item in self.constructions
            )
        )


class ConjugationPattern(ContractModel):
    """Metadata for a named algorithm implemented in Python (never executable data)."""

    pattern_id: str = Field(pattern=r"^[a-z0-9]+(?:[._:-][a-z0-9]+)*$")
    group_id: VerbGroup
    family_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    algorithm_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    algorithm_version: int = Field(ge=1)
    model_verb_id: str | None = None
    review_status: ReviewStatus = ReviewStatus.DRAFT
    source_evidence: list[SourceEvidence] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_pattern_evidence(self) -> "ConjugationPattern":
        if self.review_status in {ReviewStatus.METADATA_REVIEWED, ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED} and not self.source_evidence:
            raise ValueError("reviewed patterns require source/rule-review evidence")
        return self

class ScopeKind(str, Enum):
    ALL = "all"
    GROUP = "group"
    FAMILY = "family"
    COLLECTION = "collection"


class MembershipPolicy(str, Enum):
    ALL_APPROVED_VERBS = "all_approved_verbs"
    GROUP_MEMBERSHIP = "group_membership"
    REGISTERED_PATTERNS = "registered_patterns"
    EXPLICIT_VERB_IDS = "explicit_verb_ids"
    PATTERNS_AND_EXPLICIT_IDS = "patterns_and_explicit_ids"


class ScopeStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    RETIRED = "retired"


class CatalogScope(ContractModel):
    """Stable selector entry for a verb group, morphology family or curated set."""

    scope_id: str = Field(pattern=r"^(all|group|family|collection):[a-z0-9_]+$")
    kind: ScopeKind
    label_es: str = Field(min_length=2, max_length=120)
    label_fr: str | None = Field(default=None, max_length=120)
    group_id: VerbGroup | None = None
    membership_policy: MembershipPolicy
    pattern_ids: list[str] = Field(default_factory=list, max_length=100)
    verb_ids: list[str] = Field(default_factory=list, max_length=1000)
    status: ScopeStatus = ScopeStatus.PLANNED
    display_order: int = Field(ge=0)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_scope(self) -> "CatalogScope":
        expected_prefix = {
            ScopeKind.ALL: "all:",
            ScopeKind.GROUP: "group:",
            ScopeKind.FAMILY: "family:",
            ScopeKind.COLLECTION: "collection:",
        }[self.kind]
        if not self.scope_id.startswith(expected_prefix):
            raise ValueError(f"{self.kind.value} scope_id must start with {expected_prefix}")
        if len(set(self.pattern_ids)) != len(self.pattern_ids):
            raise ValueError("pattern_ids must be unique")
        if len(set(self.verb_ids)) != len(self.verb_ids):
            raise ValueError("verb_ids must be unique")
        if self.kind == ScopeKind.ALL:
            if self.membership_policy != MembershipPolicy.ALL_APPROVED_VERBS:
                raise ValueError("all scopes require the all_approved_verbs membership policy")
            if self.group_id is not None or self.pattern_ids or self.verb_ids:
                raise ValueError("all scopes derive membership from all approved verb records")
        if self.kind in {ScopeKind.GROUP, ScopeKind.FAMILY} and self.group_id is None:
            raise ValueError("group and family scopes require group_id")
        if self.kind == ScopeKind.COLLECTION and self.group_id is not None:
            raise ValueError("curated collections must not masquerade as a grammatical group")
        if self.kind == ScopeKind.GROUP:
            if self.membership_policy != MembershipPolicy.GROUP_MEMBERSHIP:
                raise ValueError("group scopes derive membership from group_id")
            if self.pattern_ids or self.verb_ids:
                raise ValueError("group scopes must not duplicate membership with explicit IDs")
        if self.kind == ScopeKind.FAMILY:
            if self.membership_policy == MembershipPolicy.GROUP_MEMBERSHIP:
                raise ValueError("families require patterns, explicit members or both")
            if self.membership_policy == MembershipPolicy.REGISTERED_PATTERNS:
                if not self.pattern_ids:
                    raise ValueError("pattern-based family requires pattern_ids")
                if self.verb_ids:
                    raise ValueError("registered-pattern families cannot also declare explicit verb_ids")
            if self.membership_policy == MembershipPolicy.EXPLICIT_VERB_IDS:
                if not self.verb_ids:
                    raise ValueError("explicit family requires verb_ids")
                if self.pattern_ids:
                    raise ValueError("explicit-member families cannot also declare pattern_ids")
            if self.membership_policy == MembershipPolicy.PATTERNS_AND_EXPLICIT_IDS and not (self.pattern_ids or self.verb_ids):
                raise ValueError("family requires pattern_ids and/or verb_ids")
        if self.kind == ScopeKind.COLLECTION:
            if self.membership_policy not in {
                MembershipPolicy.EXPLICIT_VERB_IDS,
                MembershipPolicy.PATTERNS_AND_EXPLICIT_IDS,
            }:
                raise ValueError("collections require an explicit membership rule")
            if self.membership_policy == MembershipPolicy.EXPLICIT_VERB_IDS and self.pattern_ids:
                raise ValueError("explicit-member collections cannot also declare pattern_ids")
            if self.status == ScopeStatus.ACTIVE and not (self.verb_ids or self.pattern_ids):
                raise ValueError("active collection requires explicit members or patterns")
        if self.status == ScopeStatus.ACTIVE:
            if self.kind == ScopeKind.FAMILY and not (self.pattern_ids or self.verb_ids):
                raise ValueError("active family requires audited membership")
            if self.kind == ScopeKind.GROUP and self.group_id is None:
                raise ValueError("active group requires group_id")
        return self
