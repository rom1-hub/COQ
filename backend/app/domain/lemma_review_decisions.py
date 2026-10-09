"""Declarative linguistic-owner decisions and source evidence.

Decisions preserve the original source token, record the chosen canonicalization
policy, and attach source evidence without embedding lexeme-specific conditions
in the auditor. A lexical decision never approves conjugation forms.
"""
from __future__ import annotations

import unicodedata
from datetime import date
from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from app.domain.candidate_lexicon import candidate_id_for, normalize_candidate_form
from app.domain.catalog_findings import CandidateAuditFlag
from app.domain.verb_contracts import ContractModel, VerbGroup


DecisionScope = Literal["candidate", "editorial_observation"]
DecisionOutcome = Literal["lemma_metadata_reviewed", "source_token_not_canonical_lemma"]
ConstructionPolicy = Literal["pronominal_only", "non_pronominal_only", "multiple_constructions"]
EvidenceKind = Literal["official_conjugation_table", "official_dictionary_entry", "third_party_lexicon"]


class DecisionEvidence(ContractModel):
    """Traceable source claim used to support a lexical review decision."""

    evidence_id: str = Field(pattern=r"^EVD-[A-Z0-9-]{2,40}$")
    evidence_kind: EvidenceKind
    source_url: HttpUrl
    supports: str = Field(min_length=10, max_length=700)
    consulted_on: date

    @model_validator(mode="after")
    def validate_source_url(self) -> "DecisionEvidence":
        if self.source_url.scheme != "https":
            raise ValueError("source_url must use HTTPS")
        return self


class LemmaReviewDecision(ContractModel):
    """A schema-validated, human-authored lexical review decision."""

    schema_version: Literal["1.3"] = "1.3"
    decision_id: str = Field(pattern=r"^LR-[0-9]{3}$")
    decision_scope: DecisionScope = "candidate"
    decision_outcome: DecisionOutcome
    source_candidate_id: str | None = Field(default=None, pattern=r"^cand_[0-9a-f]{16}$")
    source_candidate_form: str = Field(min_length=2, max_length=100)
    canonical_infinitive: str | None = Field(default=None, min_length=2, max_length=100)
    display_infinitive: str | None = Field(default=None, min_length=2, max_length=110)
    group_id: VerbGroup | None = None
    construction_policy: ConstructionPolicy | None = None
    pronominal_marker: Literal["se", "s'"] | None = None
    related_lemma: str | None = Field(default=None, min_length=2, max_length=100)
    related_construction: str | None = Field(default=None, min_length=2, max_length=120)
    resolves_findings: list[CandidateAuditFlag] = Field(default_factory=list)
    source_evidence: list[DecisionEvidence] = Field(default_factory=list)
    forms_review_status: Literal["pending", "not_applicable"] = "pending"
    decision_authority: Literal["linguistic_owner"] = "linguistic_owner"
    decision_note: str = Field(min_length=10, max_length=1500)
    approved_for_production: Literal[False] = False

    @model_validator(mode="after")
    def validate_review_decision(self) -> "LemmaReviewDecision":
        source_form = normalize_candidate_form(self.source_candidate_form)
        if self.source_candidate_form != source_form:
            raise ValueError("source_candidate_form must preserve normalized source token")

        if self.decision_scope == "candidate":
            if self.source_candidate_id is None:
                raise ValueError("candidate decisions must identify source_candidate_id")
            if self.source_candidate_id != candidate_id_for(self.source_candidate_form):
                raise ValueError("source_candidate_id must identify source_candidate_form")
        elif self.source_candidate_id is not None:
            raise ValueError("editorial observations must not claim an imported source_candidate_id")

        if len(self.resolves_findings) != len(set(self.resolves_findings)):
            raise ValueError("resolves_findings must not contain duplicates")
        evidence_ids = [item.evidence_id for item in self.source_evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("source_evidence evidence_id values must be unique within a decision")
        evidence_urls = [str(item.source_url) for item in self.source_evidence]
        if len(evidence_urls) != len(set(evidence_urls)):
            raise ValueError("source_evidence source URLs must be unique within a decision")

        if self.related_lemma is not None:
            related = unicodedata.normalize("NFC", self.related_lemma)
            if self.related_lemma != related.lower() or not all(char.isalpha() for char in self.related_lemma):
                raise ValueError("related_lemma must be a lowercase NFC infinitive token containing letters only")
        if self.related_construction is not None and self.related_lemma is None:
            raise ValueError("related_construction requires related_lemma")

        if self.decision_outcome == "lemma_metadata_reviewed":
            if self.decision_scope != "candidate":
                raise ValueError("editorial observations cannot establish imported candidate metadata")
            if any(value is None for value in (
                self.canonical_infinitive, self.display_infinitive, self.group_id, self.construction_policy
            )):
                raise ValueError("metadata-reviewed decisions require canonical infinitive, display form, group and construction")
            if self.related_lemma is not None or self.related_construction is not None:
                raise ValueError("metadata-reviewed lemma decisions cannot declare a related lemma")
            canonical = unicodedata.normalize("NFC", self.canonical_infinitive or "")
            if self.canonical_infinitive != canonical.lower():
                raise ValueError("canonical_infinitive must use lowercase NFC")
            if not all(char.isalpha() for char in self.canonical_infinitive or ""):
                raise ValueError("canonical_infinitive must contain letters only; no spaces, hyphens or pronoun")
            if self.construction_policy == "pronominal_only":
                if self.pronominal_marker is None:
                    raise ValueError("pronominal-only decisions must declare pronominal_marker (se or s-apostrophe)")
                expected_display = (
                    f"s'{self.canonical_infinitive}"
                    if self.pronominal_marker == "s'"
                    else f"se {self.canonical_infinitive}"
                )
                if self.display_infinitive != expected_display:
                    raise ValueError(
                        "pronominal display_infinitive must match its explicit pronominal_marker and canonical infinitive; no hyphenated variant is accepted"
                    )
            elif self.pronominal_marker is not None:
                raise ValueError("pronominal_marker is only valid for pronominal-only decisions")
            elif self.display_infinitive != self.canonical_infinitive:
                raise ValueError("non-pronominal/multiple display_infinitive must match canonical infinitive")
            if self.forms_review_status != "pending":
                raise ValueError("metadata-reviewed lemma forms must remain pending until their conjugations are reviewed")
        else:
            # The source token is not accepted as a separate canonical COQ lemma.
            # This does not assert that every occurrence is non-verbal: lexical
            # sources may document discouraged, archaic or colloquial infinitives.
            if any(value is not None for value in (
                self.canonical_infinitive, self.display_infinitive, self.group_id,
                self.construction_policy, self.pronominal_marker,
            )):
                raise ValueError("non-canonical source-token decisions cannot populate canonical verb metadata")
            if self.related_lemma is None:
                raise ValueError("non-canonical source-token decisions must link to the related canonical lemma")
            if self.forms_review_status != "not_applicable":
                raise ValueError("non-canonical source-token decisions must use forms_review_status='not_applicable'")

        if self.approved_for_production:
            raise ValueError("lexical review decisions cannot approve a verb for production")
        return self
