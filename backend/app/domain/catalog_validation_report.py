"""Stable response contract for COQ's catalogue validation command.

The validator is used both from developer tooling and CI. Its report shape is
versioned in code so summary counters cannot silently disappear between
releases (for example, the number of recorded linguistic lemma decisions).
"""
from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator

from app.domain.verb_contracts import ContractModel


class CatalogValidationReport(ContractModel):
    """Machine-readable validation result; this is not a production approval."""

    valid: bool
    ready_for_production: bool
    verb_count: int = Field(ge=0)
    approved_verb_count: int = Field(ge=0)
    candidate_infinitive_count: int = Field(ge=0)
    lemma_review_decision_count: int = Field(ge=0)
    pattern_count: int = Field(ge=0)
    scope_count: int = Field(ge=0)
    warnings: list[str]
    errors: list[str]

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_report_consistency(self) -> "CatalogValidationReport":
        if self.approved_verb_count > self.verb_count:
            raise ValueError("approved_verb_count cannot exceed verb_count")
        if self.valid != (len(self.errors) == 0):
            raise ValueError("valid must be true exactly when errors is empty")
        if self.ready_for_production and not self.valid:
            raise ValueError("a catalogue with validation errors cannot be ready for production")
        if self.ready_for_production and self.approved_verb_count == 0:
            raise ValueError("a production-ready catalogue must contain an approved verb")
        return self
