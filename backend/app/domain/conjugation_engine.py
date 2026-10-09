"""Pure, allow-listed conjugation engine for reviewed COQ catalogue records.

This first increment implements only the explicitly registered algorithm
``first_group_regular_er``. It is intentionally not a verb-catalog loader or
an API endpoint. All input records must already have passed catalogue review.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.domain.verb_contracts import (
    COMPOUND_AUXILIARY_TENSE,
    COMPOUND_FORMS,
    NON_PERSONAL_FORMS,
    PERSONAL_FORMS,
    AvailabilityStatus,
    Auxiliary,
    ConstructionKind,
    ConstructionProfile,
    ConjugationPattern,
    FormContext,
    FormAvailability,
    FormOverride,
    FormId,
    Gender,
    GrammaticalNumber,
    ParticipleAgreementPolicy,
    PersonId,
    ReviewStatus,
    VerbRecord,
    VerbGroup,
)


@dataclass(frozen=True)
class GeneratedForm:
    """A target verbal group, excluding the grammatical subject and subjunctive ``que``."""

    form_id: FormId
    context: FormContext
    preferred_form: str
    accepted_forms: tuple[str, ...]
    algorithm_key: str
    used_override: bool = False


class ConjugationEngineError(RuntimeError):
    """Base class for safe, caller-displayable domain failures."""

    code = "CONJUGATION_ENGINE_ERROR"


class UnapprovedRecordError(ConjugationEngineError):
    code = "UNAPPROVED_RECORD"


class PatternMismatchError(ConjugationEngineError):
    code = "PATTERN_MISMATCH"


class UnsupportedPatternError(ConjugationEngineError):
    code = "UNSUPPORTED_PATTERN"


class InvalidFormContextError(ConjugationEngineError):
    code = "INVALID_FORM_CONTEXT"


class FormUnavailableError(ConjugationEngineError):
    code = "FORM_UNAVAILABLE"


class FormNotReviewedError(ConjugationEngineError):
    code = "FORM_NOT_REVIEWED"


class CatalogConflictError(ConjugationEngineError):
    code = "CATALOG_CONFLICT"


# These are the only executable algorithms available in this first increment.
# A key in JSON is never imported or evaluated dynamically.
SUPPORTED_ALGORITHM_VERSIONS = {"first_group_regular_er": 1}

_PRESENT_ENDINGS = {
    PersonId.JE: "e",
    PersonId.TU: "es",
    PersonId.IL: "e",
    PersonId.ELLE: "e",
    PersonId.ON: "e",
    PersonId.NOUS: "ons",
    PersonId.VOUS: "ez",
    PersonId.ILS: "ent",
    PersonId.ELLES: "ent",
}
_IMPARFAIT_ENDINGS = {
    PersonId.JE: "ais",
    PersonId.TU: "ais",
    PersonId.IL: "ait",
    PersonId.ELLE: "ait",
    PersonId.ON: "ait",
    PersonId.NOUS: "ions",
    PersonId.VOUS: "iez",
    PersonId.ILS: "aient",
    PersonId.ELLES: "aient",
}
_CONDITIONAL_ENDINGS = _IMPARFAIT_ENDINGS
_FUTURE_ENDINGS = {
    PersonId.JE: "ai",
    PersonId.TU: "as",
    PersonId.IL: "a",
    PersonId.ELLE: "a",
    PersonId.ON: "a",
    PersonId.NOUS: "ons",
    PersonId.VOUS: "ez",
    PersonId.ILS: "ont",
    PersonId.ELLES: "ont",
}
_SUBJONCTIF_ENDINGS = {
    PersonId.JE: "e",
    PersonId.TU: "es",
    PersonId.IL: "e",
    PersonId.ELLE: "e",
    PersonId.ON: "e",
    PersonId.NOUS: "ions",
    PersonId.VOUS: "iez",
    PersonId.ILS: "ent",
    PersonId.ELLES: "ent",
}

# Internal auxiliary paradigms needed to assemble COQ compound tenses. These
# tables are keyed by the declared Auxiliary field, not by arbitrary infinitive.
_AUXILIARY_PARADIGMS = {
    Auxiliary.AVOIR: {
        FormId.PRESENT_INDICATIF: {
            PersonId.JE: "ai", PersonId.TU: "as", PersonId.IL: "a",
            PersonId.ELLE: "a", PersonId.ON: "a", PersonId.NOUS: "avons",
            PersonId.VOUS: "avez", PersonId.ILS: "ont", PersonId.ELLES: "ont",
        },
        FormId.IMPARFAIT: {
            PersonId.JE: "avais", PersonId.TU: "avais", PersonId.IL: "avait",
            PersonId.ELLE: "avait", PersonId.ON: "avait", PersonId.NOUS: "avions",
            PersonId.VOUS: "aviez", PersonId.ILS: "avaient", PersonId.ELLES: "avaient",
        },
        FormId.CONDITIONNEL_PRESENT: {
            PersonId.JE: "aurais", PersonId.TU: "aurais", PersonId.IL: "aurait",
            PersonId.ELLE: "aurait", PersonId.ON: "aurait", PersonId.NOUS: "aurions",
            PersonId.VOUS: "auriez", PersonId.ILS: "auraient", PersonId.ELLES: "auraient",
        },
        FormId.FUTUR_SIMPLE: {
            PersonId.JE: "aurai", PersonId.TU: "auras", PersonId.IL: "aura",
            PersonId.ELLE: "aura", PersonId.ON: "aura", PersonId.NOUS: "aurons",
            PersonId.VOUS: "aurez", PersonId.ILS: "auront", PersonId.ELLES: "auront",
        },
        FormId.SUBJONCTIF_PRESENT: {
            PersonId.JE: "aie", PersonId.TU: "aies", PersonId.IL: "ait",
            PersonId.ELLE: "ait", PersonId.ON: "ait", PersonId.NOUS: "ayons",
            PersonId.VOUS: "ayez", PersonId.ILS: "aient", PersonId.ELLES: "aient",
        },
    },
    Auxiliary.ETRE: {
        FormId.PRESENT_INDICATIF: {
            PersonId.JE: "suis", PersonId.TU: "es", PersonId.IL: "est",
            PersonId.ELLE: "est", PersonId.ON: "est", PersonId.NOUS: "sommes",
            PersonId.VOUS: "êtes", PersonId.ILS: "sont", PersonId.ELLES: "sont",
        },
        FormId.IMPARFAIT: {
            PersonId.JE: "étais", PersonId.TU: "étais", PersonId.IL: "était",
            PersonId.ELLE: "était", PersonId.ON: "était", PersonId.NOUS: "étions",
            PersonId.VOUS: "étiez", PersonId.ILS: "étaient", PersonId.ELLES: "étaient",
        },
        FormId.CONDITIONNEL_PRESENT: {
            PersonId.JE: "serais", PersonId.TU: "serais", PersonId.IL: "serait",
            PersonId.ELLE: "serait", PersonId.ON: "serait", PersonId.NOUS: "serions",
            PersonId.VOUS: "seriez", PersonId.ILS: "seraient", PersonId.ELLES: "seraient",
        },
        FormId.FUTUR_SIMPLE: {
            PersonId.JE: "serai", PersonId.TU: "seras", PersonId.IL: "sera",
            PersonId.ELLE: "sera", PersonId.ON: "sera", PersonId.NOUS: "serons",
            PersonId.VOUS: "serez", PersonId.ILS: "seront", PersonId.ELLES: "seront",
        },
        FormId.SUBJONCTIF_PRESENT: {
            PersonId.JE: "sois", PersonId.TU: "sois", PersonId.IL: "soit",
            PersonId.ELLE: "soit", PersonId.ON: "soit", PersonId.NOUS: "soyons",
            PersonId.VOUS: "soyez", PersonId.ILS: "soient", PersonId.ELLES: "soient",
        },
    },
}

_REFLEXIVE_CLITICS = {
    PersonId.JE: "me",
    PersonId.TU: "te",
    PersonId.IL: "se",
    PersonId.ELLE: "se",
    PersonId.ON: "se",
    PersonId.NOUS: "nous",
    PersonId.VOUS: "vous",
    PersonId.ILS: "se",
    PersonId.ELLES: "se",
}
_IMPERATIVE_ENCLITICS = {
    PersonId.TU: "toi",
    PersonId.NOUS: "nous",
    PersonId.VOUS: "vous",
}
_VOWELS = frozenset("aeiouyàâäéèêëîïôöùûüÿœæ")


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _same_context(left: FormContext, right: FormContext) -> bool:
    return (
        left.person == right.person
        and left.gender == right.gender
        and left.number == right.number
        and left.usage == right.usage
    )


def _is_agreement_context(context: FormContext) -> bool:
    return context.gender is not None and context.number is not None


def _validated_context(form_id: FormId, context: FormContext | None) -> FormContext:
    ctx = context or FormContext()
    if form_id in PERSONAL_FORMS and ctx.person is None:
        raise InvalidFormContextError(f"{form_id.value} requires a person context")
    if form_id in COMPOUND_FORMS and not _is_agreement_context(ctx):
        raise InvalidFormContextError(f"{form_id.value} requires gender and number context")
    if form_id in PERSONAL_FORMS and form_id not in COMPOUND_FORMS and _is_agreement_context(ctx):
        raise InvalidFormContextError(f"{form_id.value} does not accept agreement context")
    if form_id in NON_PERSONAL_FORMS and ctx.person is not None:
        raise InvalidFormContextError(f"{form_id.value} does not accept person context")
    if form_id == FormId.IMPERATIF_PRESENT and ctx.person not in {
        PersonId.TU, PersonId.NOUS, PersonId.VOUS
    }:
        raise InvalidFormContextError("imperatif_present requires tu, nous or vous")
    if form_id in {FormId.PARTICIPE_PRESENT, FormId.GERONDIF_PRESENT} and _is_agreement_context(ctx):
        raise InvalidFormContextError(f"{form_id.value} does not accept agreement context")
    return ctx


class ConjugationEngine:
    """Generate a form only from approved records and an explicit allow-listed algorithm."""

    def generate(
        self,
        verb: VerbRecord,
        pattern: ConjugationPattern,
        construction_id: str,
        form_id: FormId,
        context: FormContext | None = None,
    ) -> GeneratedForm:
        if form_id == FormId.PARTICIPE_PASSE:
            raise InvalidFormContextError("participe_passe is internal and cannot be requested directly")
        context = _validated_context(form_id, context)
        construction = self._require_approved_records(verb, pattern, construction_id)
        self._validate_pattern_for_verb(verb, pattern)

        availability = self._matching_availability(construction, form_id, context)
        if availability is not None:
            if availability.status == AvailabilityStatus.UNAVAILABLE:
                raise FormUnavailableError(availability.reason)
            if availability.status == AvailabilityStatus.NOT_REVIEWED:
                raise FormNotReviewedError(availability.reason)

        direct_override = self._matching_override(construction, form_id, context)
        if direct_override is not None and direct_override.review_status not in {
            ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED
        }:
            raise FormNotReviewedError(
                f"{form_id.value} has a matching override that has not completed form review"
            )

        # Explicit compound-form overrides already contain the full verbal group
        # (including a reflexive clitic where applicable), but never subject/que.
        if direct_override is not None and direct_override.operation == "replace":
            forms = direct_override.accepted_forms
            return self._result(form_id, context, forms, pattern, used_override=True)

        self._require_explicit_availability_for_special_verb(verb, construction, form_id, context, direct_override)
        base_forms = self._generate_base(verb, construction, form_id, context)

        used_override = form_id in COMPOUND_FORMS and self._has_participle_override(construction, context)
        if direct_override is not None:
            if direct_override.operation == "add":
                base_forms = _dedupe((*base_forms, *direct_override.accepted_forms))
            used_override = True
        return self._result(form_id, context, base_forms, pattern, used_override=used_override)

    @staticmethod
    def _result(
        form_id: FormId,
        context: FormContext,
        forms: Iterable[str],
        pattern: ConjugationPattern,
        *,
        used_override: bool,
    ) -> GeneratedForm:
        accepted = _dedupe(forms)
        if not accepted:
            raise FormNotReviewedError(f"No accepted forms are registered for {form_id.value}")
        return GeneratedForm(
            form_id=form_id,
            context=context,
            preferred_form=accepted[0],
            accepted_forms=accepted,
            algorithm_key=pattern.algorithm_key,
            used_override=used_override,
        )

    @staticmethod
    def _require_approved_records(
        verb: VerbRecord, pattern: ConjugationPattern, construction_id: str
    ) -> ConstructionProfile:
        if verb.review_status != ReviewStatus.APPROVED:
            raise UnapprovedRecordError(f"Verb {verb.verb_id} is not approved for production")
        if pattern.review_status != ReviewStatus.APPROVED:
            raise UnapprovedRecordError(f"Pattern {pattern.pattern_id} is not approved for production")
        if verb.pattern_id != pattern.pattern_id:
            raise PatternMismatchError("Verb pattern_id does not match the supplied pattern")
        construction = next(
            (item for item in verb.constructions if item.construction_id == construction_id), None
        )
        if construction is None:
            raise PatternMismatchError(f"Construction {construction_id!r} does not belong to {verb.verb_id}")
        if construction.review_status != ReviewStatus.APPROVED:
            raise UnapprovedRecordError(f"Construction {construction_id} is not approved for production")
        return construction

    @staticmethod
    def _validate_pattern_for_verb(verb: VerbRecord, pattern: ConjugationPattern) -> None:
        if verb.group_id != pattern.group_id:
            raise PatternMismatchError("Verb group does not match the supplied pattern")
        if pattern.algorithm_key not in SUPPORTED_ALGORITHM_VERSIONS:
            raise UnsupportedPatternError(f"No implementation is registered for {pattern.algorithm_key!r}")
        if pattern.algorithm_version != SUPPORTED_ALGORITHM_VERSIONS[pattern.algorithm_key]:
            raise UnsupportedPatternError(
                f"Algorithm {pattern.algorithm_key!r} does not support version {pattern.algorithm_version}"
            )
        if pattern.algorithm_key == "first_group_regular_er":
            if pattern.family_id != "first_regular":
                raise PatternMismatchError("first_group_regular_er requires pattern family first_regular")
            if pattern.family_id not in verb.family_ids:
                raise PatternMismatchError("Verb family_ids do not include the registered pattern family")
            if verb.group_id != VerbGroup.FIRST or not verb.infinitive.endswith("er"):
                raise PatternMismatchError("first_group_regular_er requires a first-group infinitive ending in -er")
            if _value(verb.regularity) != "regular":
                raise PatternMismatchError("first_group_regular_er cannot handle an orthographic or irregular verb")

    @staticmethod
    def _matching_override(
        construction: ConstructionProfile, form_id: FormId, context: FormContext
    ) -> FormOverride | None:
        exact = [
            item for item in construction.form_overrides
            if item.form_id == form_id and _same_context(item.context, context)
        ]
        if len(exact) > 1:
            raise CatalogConflictError(f"Duplicate override for {form_id.value} and its context")
        return exact[0] if exact else None

    @staticmethod
    def _matching_availability(
        construction: ConstructionProfile, form_id: FormId, context: FormContext
    ) -> FormAvailability | None:
        exact = []
        broad = []
        for item in construction.availability_overrides:
            if item.form_id != form_id:
                continue
            if _same_context(item.context, context):
                exact.append(item)
            elif (
                item.context.person is None
                and item.context.gender is None
                and item.context.number is None
                and item.context.usage is None
            ):
                broad.append(item)
        matches = exact or broad
        if len(matches) > 1:
            raise CatalogConflictError(f"Duplicate availability rules for {form_id.value} and its context")
        return matches[0] if matches else None

    @staticmethod
    def _require_explicit_availability_for_special_verb(
        verb: VerbRecord,
        construction: ConstructionProfile,
        form_id: FormId,
        context: FormContext,
        override: FormOverride | None,
    ) -> None:
        traits = set(verb.traits or [])
        if not traits.intersection({"impersonal", "defective"}):
            return
        availability = ConjugationEngine._matching_availability(construction, form_id, context)
        if override is not None and override.review_status in {ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED}:
            return
        if availability is None or availability.status != AvailabilityStatus.AVAILABLE:
            raise FormNotReviewedError(
                f"{form_id.value} needs an explicit available-form decision for this {', '.join(sorted(traits))} verb"
            )

    def _generate_base(
        self,
        verb: VerbRecord,
        construction: ConstructionProfile,
        form_id: FormId,
        context: FormContext,
    ) -> tuple[str, ...]:
        if form_id in COMPOUND_FORMS:
            return self._compound_form(verb, construction, form_id, context)
        if form_id == FormId.PARTICIPE_PASSE:
            raise InvalidFormContextError("participe_passe is internal")
        base = self._regular_er_base(verb.infinitive, form_id, context)
        if construction.kind == ConstructionKind.PRONOMINAL:
            base = self._add_pronominal_marker(base, construction, form_id, context)
        return (base,)

    @staticmethod
    def _regular_er_base(infinitive: str, form_id: FormId, context: FormContext) -> str:
        stem = infinitive[:-2]
        person = context.person
        if form_id == FormId.PRESENT_INDICATIF:
            return stem + _PRESENT_ENDINGS[person]
        if form_id == FormId.IMPERATIF_PRESENT:
            return stem + {
                PersonId.TU: "e",
                PersonId.NOUS: "ons",
                PersonId.VOUS: "ez",
            }[person]
        if form_id == FormId.IMPARFAIT:
            # This registered algorithm is strictly regular -ER, not -GER/-CER/etc.
            return stem + _IMPARFAIT_ENDINGS[person]
        if form_id == FormId.CONDITIONNEL_PRESENT:
            return infinitive + _CONDITIONAL_ENDINGS[person]
        if form_id == FormId.FUTUR_SIMPLE:
            return infinitive + _FUTURE_ENDINGS[person]
        if form_id == FormId.SUBJONCTIF_PRESENT:
            return stem + _SUBJONCTIF_ENDINGS[person]
        if form_id == FormId.PARTICIPE_PRESENT:
            return stem + "ant"
        if form_id == FormId.GERONDIF_PRESENT:
            return "en " + stem + "ant"
        if form_id == FormId.PARTICIPE_PASSE:
            return stem + "é"
        raise UnsupportedPatternError(f"first_group_regular_er does not generate {form_id.value}")

    def _compound_form(
        self,
        verb: VerbRecord,
        construction: ConstructionProfile,
        form_id: FormId,
        context: FormContext,
    ) -> tuple[str, ...]:
        auxiliary_tense = COMPOUND_AUXILIARY_TENSE[form_id]
        auxiliary = construction.auxiliary
        person = context.person
        try:
            auxiliary_form = _AUXILIARY_PARADIGMS[auxiliary][auxiliary_tense][person]
        except KeyError as exc:
            raise UnsupportedPatternError(
                f"No auxiliary form for {auxiliary.value}, {auxiliary_tense.value}, {person.value}"
            ) from exc

        participles = self._past_participle(verb, construction, context)
        if construction.kind == ConstructionKind.PRONOMINAL:
            reflexive = _REFLEXIVE_CLITICS[person]
            clitic = self._elide_clitic(reflexive, auxiliary_form, force=False)
            prefix = clitic if clitic.endswith("'") else f"{clitic} "
            return tuple(f"{prefix}{auxiliary_form} {participle}" for participle in participles)
        return tuple(f"{auxiliary_form} {participle}" for participle in participles)

    def _past_participle(
        self,
        verb: VerbRecord,
        construction: ConstructionProfile,
        compound_context: FormContext,
    ) -> tuple[str, ...]:
        target_context = FormContext(gender=compound_context.gender, number=compound_context.number)
        override = self._matching_override(construction, FormId.PARTICIPE_PASSE, target_context)
        generic_override = self._matching_override(construction, FormId.PARTICIPE_PASSE, FormContext())
        selected = override or generic_override

        if selected is not None:
            if selected.review_status not in {ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED}:
                raise FormNotReviewedError("Participe passé override has not completed form review")
            policy = construction.participle_agreement
            if policy == ParticipleAgreementPolicy.INVARIABLE and selected.context.gender is not None:
                raise CatalogConflictError("an invariable participle cannot have gender/number-specific overrides")

            forms = selected.accepted_forms
            default = self._regular_er_base(verb.infinitive, FormId.PARTICIPE_PASSE, FormContext())
            if selected.operation == "add":
                if policy == ParticipleAgreementPolicy.SUBJECT and selected.context.gender is not None:
                    default = _agree_past_participle(default, compound_context.gender, compound_context.number)
                forms = _dedupe((default, *forms))

            # Context-free values are base participles; subject-agreement policy is
            # applied only at the point where gender/number is known. Contextual
            # values are already the exact reviewed forms for this context.
            if policy == ParticipleAgreementPolicy.SUBJECT and selected.context.gender is None:
                return _dedupe(
                    _agree_past_participle(form, compound_context.gender, compound_context.number)
                    for form in forms
                )
            return _dedupe(forms)

        policy = construction.participle_agreement
        if policy == ParticipleAgreementPolicy.INVARIABLE:
            return (self._regular_er_base(verb.infinitive, FormId.PARTICIPE_PASSE, FormContext()),)
        if policy == ParticipleAgreementPolicy.SUBJECT:
            base = self._regular_er_base(verb.infinitive, FormId.PARTICIPE_PASSE, FormContext())
            return (_agree_past_participle(base, compound_context.gender, compound_context.number),)
        if policy == ParticipleAgreementPolicy.VERB_SPECIFIC:
            raise FormNotReviewedError(
                f"{verb.infinitive}: verb-specific participle agreement needs an approved contextual or invariant override"
            )
        raise UnsupportedPatternError(f"Unsupported participle policy: {policy}")

    @staticmethod
    def _has_participle_override(
        construction: ConstructionProfile, compound_context: FormContext
    ) -> bool:
        target = FormContext(gender=compound_context.gender, number=compound_context.number)
        return (
            ConjugationEngine._matching_override(construction, FormId.PARTICIPE_PASSE, target) is not None
            or ConjugationEngine._matching_override(construction, FormId.PARTICIPE_PASSE, FormContext()) is not None
        )

    def _add_pronominal_marker(
        self, form: str, construction: ConstructionProfile, form_id: FormId, context: FormContext
    ) -> str:
        person = context.person
        if form_id == FormId.IMPERATIF_PRESENT:
            enclitic = _IMPERATIVE_ENCLITICS[person]
            return f"{form}-{enclitic}"
        # Non-personal pronominal forms use the default third-person clitic.
        clitic_person = person if person is not None else PersonId.IL
        clitic = _REFLEXIVE_CLITICS[clitic_person]
        if form_id == FormId.GERONDIF_PRESENT:
            # The gérondif includes en; the reflexive clitic stays after en.
            participle = form.removeprefix("en ")
            clitic = self._elide_clitic(clitic, participle, force=self._display_infinitive_is_elided(construction))
            prefix = clitic if clitic.endswith("'") else f"{clitic} "
            return f"en {prefix}{participle}"
        if form_id == FormId.PARTICIPE_PRESENT:
            clitic = self._elide_clitic(clitic, form, force=self._display_infinitive_is_elided(construction))
            prefix = clitic if clitic.endswith("'") else f"{clitic} "
            return f"{prefix}{form}"
        clitic = self._elide_clitic(clitic, form, force=self._display_infinitive_is_elided(construction))
        prefix = clitic if clitic.endswith("'") else f"{clitic} "
        return f"{prefix}{form}"

    @staticmethod
    def _display_infinitive_is_elided(construction: ConstructionProfile) -> bool:
        surface = construction.display_infinitive.strip().casefold().replace("’", "'")
        return surface.startswith("s'")

    @staticmethod
    def _elide_clitic(clitic: str, following: str, *, force: bool) -> str:
        normalized = following.lstrip().casefold().replace("’", "'")
        starts_vowel = bool(normalized) and normalized[0] in _VOWELS
        if (starts_vowel or force) and clitic in {"me", "te", "se"}:
            return {"me": "m'", "te": "t'", "se": "s'"}[clitic]
        return clitic


def _agree_past_participle(base: str, gender: Gender | None, number: GrammaticalNumber | None) -> str:
    if gender is None or number is None:
        raise InvalidFormContextError("past-participle agreement requires gender and number")
    result = base
    if gender == Gender.FEMININE and not result.endswith("e"):
        result += "e"
    if number == GrammaticalNumber.PLURAL and not result.endswith("s"):
        result += "s"
    return result


def _dedupe(forms: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for form in forms:
        cleaned = form.strip()
        if cleaned and cleaned not in seen:
            result.append(cleaned)
            seen.add(cleaned)
    return tuple(result)
