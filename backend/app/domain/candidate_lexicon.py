"""Candidate-only lexicon records imported from a licensed verb-name list.

These records are never eligible for conjugation lookup or practice. They are a
review queue and must be transformed into approved VerbRecord entries manually.
"""
from __future__ import annotations

import hashlib
import unicodedata
from typing import Literal

from pydantic import Field, model_validator

from app.domain.verb_contracts import ContractModel, VerbGroup


CANDIDATE_SOURCE_ID = "einenlum/french-verbs-list"
CANDIDATE_SOURCE_COMMIT = "6fee12e56eb6b5863f3410644b4164491267fb7e"


def normalize_candidate_form(value: str) -> str:
    """Normalize whitespace, Unicode composition and case without deleting accents."""
    normalized = unicodedata.normalize("NFC", " ".join(value.split())).lower()
    return normalized


def candidate_id_for(value: str) -> str:
    normalized = normalize_candidate_form(value)
    return "cand_" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


class CandidateInfinitiveRecord(ContractModel):
    """An unreviewed source token, not a canonical verb record."""

    schema_version: Literal["1.0"] = "1.0"
    candidate_id: str = Field(pattern=r"^cand_[0-9a-f]{16}$")
    candidate_form: str = Field(min_length=2, max_length=100)
    suggested_groups: list[VerbGroup] = Field(min_length=1, max_length=3)
    source_id: Literal["einenlum/french-verbs-list"] = CANDIDATE_SOURCE_ID
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    review_status: Literal["candidate"] = "candidate"
    group_suggestions_are_unverified: Literal[True] = True
    requires_lemma_review: Literal[True] = True

    @model_validator(mode="after")
    def validate_candidate_record(self) -> "CandidateInfinitiveRecord":
        if self.candidate_form != normalize_candidate_form(self.candidate_form):
            raise ValueError("candidate_form must be normalized to NFC, lowercase and single spaces")
        if self.candidate_id != candidate_id_for(self.candidate_form):
            raise ValueError("candidate_id must be the stable hash of candidate_form")
        if len(self.suggested_groups) != len(set(self.suggested_groups)):
            raise ValueError("suggested_groups must not contain duplicates")
        return self
