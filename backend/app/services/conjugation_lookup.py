"""Use case for public conjugation lookup through the approved catalogue."""
from __future__ import annotations

from collections.abc import Iterable

from app.api.contracts import (
    ApiErrorCode,
    ConjugationLookupResponse,
    ConjugationRowResponse,
    ConjugationTableResponse,
    SELECTABLE_FORM_IDS,
)
from app.api.errors import ApiProblem
from app.domain.conjugation_engine import (
    CatalogConflictError,
    ConjugationEngine,
    FormNotReviewedError,
    FormUnavailableError,
    InvalidFormContextError,
    PatternMismatchError,
    UnapprovedRecordError,
    UnsupportedPatternError,
)
from app.domain.verb_contracts import (
    COMPOUND_FORMS,
    Auxiliary,
    ConstructionProfile,
    FormContext,
    FormId,
    Gender,
    GrammaticalNumber,
    PersonId,
    ReviewStatus,
    Usage,
    VerbRecord,
    ConjugationPattern,
)
from app.services.catalog_repository import JsonlCatalogRepository


_FORM_ORDER = [
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

_FORM_LABELS_FR = {
    FormId.PRESENT_INDICATIF: "Présent de l’indicatif",
    FormId.IMPERATIF_PRESENT: "Impératif présent",
    FormId.IMPARFAIT: "Imparfait",
    FormId.CONDITIONNEL_PRESENT: "Conditionnel présent",
    FormId.FUTUR_SIMPLE: "Futur simple",
    FormId.SUBJONCTIF_PRESENT: "Subjonctif présent",
    FormId.PASSE_COMPOSE: "Passé composé",
    FormId.PLUS_QUE_PARFAIT: "Plus-que-parfait",
    FormId.CONDITIONNEL_PASSE: "Conditionnel passé",
    FormId.FUTUR_ANTERIEUR: "Futur antérieur",
    FormId.SUBJONCTIF_PASSE: "Subjonctif passé",
    FormId.PARTICIPE_PRESENT: "Participe présent",
    FormId.GERONDIF_PRESENT: "Gérondif présent",
}

_PERSON_ORDER = [
    PersonId.JE,
    PersonId.TU,
    PersonId.IL,
    PersonId.ELLE,
    PersonId.ON,
    PersonId.NOUS,
    PersonId.VOUS,
    PersonId.ILS,
    PersonId.ELLES,
]

_GENDER_ES = {
    Gender.MASCULINE: "masculino",
    Gender.FEMININE: "femenino",
}
_NUMBER_ES = {
    GrammaticalNumber.SINGULAR: "singular",
    GrammaticalNumber.PLURAL: "plural",
}


def _context(person: PersonId, gender: Gender, number: GrammaticalNumber, usage: Usage | None = None) -> FormContext:
    return FormContext(person=person, gender=gender, number=number, usage=usage)


def _contexts_for_form(form_id: FormId) -> tuple[FormContext, ...]:
    if form_id == FormId.IMPERATIF_PRESENT:
        return (
            FormContext(person=PersonId.TU),
            FormContext(person=PersonId.NOUS),
            FormContext(person=PersonId.VOUS, usage=Usage.STANDARD),
        )
    if form_id in COMPOUND_FORMS:
        # COQ's approved nine subjects and agreement contexts, including all
        # three agreed "on" contexts and courtesy/plural "vous" contexts.
        return (
            _context(PersonId.JE, Gender.MASCULINE, GrammaticalNumber.SINGULAR),
            _context(PersonId.JE, Gender.FEMININE, GrammaticalNumber.SINGULAR),
            _context(PersonId.TU, Gender.MASCULINE, GrammaticalNumber.SINGULAR),
            _context(PersonId.TU, Gender.FEMININE, GrammaticalNumber.SINGULAR),
            _context(PersonId.IL, Gender.MASCULINE, GrammaticalNumber.SINGULAR),
            _context(PersonId.ELLE, Gender.FEMININE, GrammaticalNumber.SINGULAR),
            _context(PersonId.ON, Gender.MASCULINE, GrammaticalNumber.SINGULAR),
            _context(PersonId.ON, Gender.MASCULINE, GrammaticalNumber.PLURAL),
            _context(PersonId.ON, Gender.FEMININE, GrammaticalNumber.PLURAL),
            _context(PersonId.NOUS, Gender.MASCULINE, GrammaticalNumber.PLURAL),
            _context(PersonId.NOUS, Gender.FEMININE, GrammaticalNumber.PLURAL),
            _context(PersonId.VOUS, Gender.MASCULINE, GrammaticalNumber.SINGULAR, Usage.COURTESY),
            _context(PersonId.VOUS, Gender.FEMININE, GrammaticalNumber.SINGULAR, Usage.COURTESY),
            _context(PersonId.VOUS, Gender.MASCULINE, GrammaticalNumber.PLURAL, Usage.STANDARD),
            _context(PersonId.VOUS, Gender.FEMININE, GrammaticalNumber.PLURAL, Usage.STANDARD),
            _context(PersonId.ILS, Gender.MASCULINE, GrammaticalNumber.PLURAL),
            _context(PersonId.ELLES, Gender.FEMININE, GrammaticalNumber.PLURAL),
        )
    if form_id in SELECTABLE_FORM_IDS and form_id not in {
        FormId.PARTICIPE_PRESENT,
        FormId.GERONDIF_PRESENT,
    }:
        rows = []
        for person in _PERSON_ORDER:
            if person == PersonId.VOUS:
                rows.append(FormContext(person=person, usage=Usage.STANDARD))
            else:
                rows.append(FormContext(person=person))
        return tuple(rows)
    return (FormContext(),)


def _display_subject(context: FormContext) -> str | None:
    person = context.person
    if person is None:
        return None
    if context.gender is None or context.number is None:
        return person.value
    details = f"{_GENDER_ES[context.gender]} {_NUMBER_ES[context.number]}"
    if context.usage == Usage.COURTESY:
        details = f"de cortesía, {details}"
    return f"{person.value} ({details})"


class ConjugationLookupService:
    """Build response tables using only approved verbs, patterns and constructions."""

    def __init__(
        self,
        repository: JsonlCatalogRepository,
        engine: ConjugationEngine | None = None,
    ) -> None:
        self.repository = repository
        self.engine = engine or ConjugationEngine()

    def lookup(
        self,
        verb_id: str,
        form_ids: list[FormId] | None = None,
        construction_id: str | None = None,
    ) -> ConjugationLookupResponse:
        if not self.repository.production_ready:
            raise ApiProblem(
                503,
                ApiErrorCode.CATALOG_NOT_READY,
                "El catálogo de conjugación todavía no está listo para consultas.",
            )

        verb = self.repository.verb_by_id(verb_id)
        if verb is None:
            raise ApiProblem(404, ApiErrorCode.VERB_NOT_FOUND, "No se encontró ese verbo aprobado.")

        if verb.review_status != ReviewStatus.APPROVED or not verb.is_approved_for_practice:
            raise ApiProblem(
                409,
                ApiErrorCode.VERB_NOT_APPROVED,
                "Este verbo todavía no está aprobado para consulta.",
            )

        if not verb.pattern_id:
            raise ApiProblem(
                503, ApiErrorCode.CATALOG_NOT_READY,
                "El registro del verbo todavía no tiene un patrón validado.",
            )
        pattern = self.repository.pattern_by_id(verb.pattern_id)
        if pattern is None or pattern.review_status != ReviewStatus.APPROVED:
            raise ApiProblem(
                503, ApiErrorCode.CATALOG_NOT_READY,
                "El patrón de este verbo todavía no está aprobado.",
            )

        requested_construction_id = construction_id or verb.default_construction_id
        construction = next(
            (item for item in verb.constructions if item.construction_id == requested_construction_id),
            None,
        )
        if construction is None or construction.review_status != ReviewStatus.APPROVED:
            raise ApiProblem(
                409,
                ApiErrorCode.CONSTRUCTION_NOT_AVAILABLE,
                "La construcción seleccionada no está disponible para este verbo.",
            )

        selected_forms = list(form_ids) if form_ids is not None else list(_FORM_ORDER)
        if not selected_forms:
            raise ApiProblem(422, ApiErrorCode.INVALID_REQUEST, "Debe seleccionar al menos una forma verbal.")
        if len(selected_forms) != len(set(selected_forms)):
            raise ApiProblem(422, ApiErrorCode.INVALID_REQUEST, "No se pueden repetir formas verbales.")
        if any(form_id not in SELECTABLE_FORM_IDS for form_id in selected_forms):
            raise ApiProblem(422, ApiErrorCode.INVALID_REQUEST, "La solicitud contiene una forma no seleccionable.")

        tables: list[ConjugationTableResponse] = []
        for form_id in selected_forms:
            table = self._build_table(verb, pattern, construction, form_id, explicit=form_ids is not None)
            if table is not None:
                tables.append(table)

        if not tables:
            raise ApiProblem(
                422,
                ApiErrorCode.FORM_NOT_AVAILABLE,
                "No hay formas revisadas y disponibles para la selección solicitada.",
            )

        sources: list[str] = []
        evidence_groups: Iterable[object] = (
            *verb.source_evidence,
            *construction.source_evidence,
            *pattern.source_evidence,
        )
        for item in evidence_groups:
            source_url = getattr(item, "url", None)
            if source_url:
                normalized = str(source_url)
                if normalized not in sources:
                    sources.append(normalized)

        return ConjugationLookupResponse(
            verb_id=verb.verb_id,
            infinitive=verb.infinitive,
            construction_id=construction.construction_id,
            tables=tables,
            source_urls=sources,
        )

    def _build_table(
        self,
        verb: VerbRecord,
        pattern: ConjugationPattern,
        construction: ConstructionProfile,
        form_id: FormId,
        *,
        explicit: bool,
    ) -> ConjugationTableResponse | None:
        rows: list[ConjugationRowResponse] = []
        for context in _contexts_for_form(form_id):
            try:
                generated = self.engine.generate(
                    verb,
                    pattern,
                    construction.construction_id,
                    form_id,
                    context,
                )
            except (FormUnavailableError, FormNotReviewedError):
                continue
            except UnsupportedPatternError as exc:
                if explicit:
                    raise ApiProblem(
                        422,
                        ApiErrorCode.FORM_NOT_AVAILABLE,
                        "Este patrón todavía no genera la forma solicitada.",
                        {"form_id": form_id.value},
                    ) from exc
                return None
            except InvalidFormContextError as exc:
                raise ApiProblem(
                    422,
                    ApiErrorCode.INVALID_REQUEST,
                    "El contexto lingüístico solicitado no es válido.",
                    {"form_id": form_id.value},
                ) from exc
            except (CatalogConflictError, PatternMismatchError, UnapprovedRecordError) as exc:
                raise ApiProblem(
                    503,
                    ApiErrorCode.CATALOG_NOT_READY,
                    "Se detectó una inconsistencia en los datos de conjugación aprobados.",
                ) from exc

            rows.append(
                ConjugationRowResponse(
                    person=context.person,
                    context=context,
                    display_subject=_display_subject(context),
                    display_forms=list(generated.accepted_forms),
                )
            )

        if not rows:
            if explicit:
                raise ApiProblem(
                    422,
                    ApiErrorCode.FORM_NOT_AVAILABLE,
                    "La forma seleccionada no tiene contextos revisados y disponibles.",
                    {"form_id": form_id.value},
                )
            return None

        return ConjugationTableResponse(
            form_id=form_id,
            label_fr=_FORM_LABELS_FR[form_id],
            rows=rows,
        )
