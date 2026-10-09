"""Stable identifiers for explainable candidate-catalogue audit findings.

This enum is shared by the generic auditor and declarative human-review decisions.
A verb-specific resolution belongs in data/catalogs/lemma-review-decisions.jsonl,
never in an `if lemma == ...` branch in code.
"""
from __future__ import annotations

from enum import Enum


class CandidateAuditFlag(str, Enum):
    FIRST_GROUP_NOT_ER = "first_group_suggestion_not_er"
    SECOND_GROUP_NOT_IR = "second_group_suggestion_not_ir"
    THIRD_GROUP_SUFFIX_MISMATCH = "third_group_suffix_mismatch"
    UNUSUAL_INFINITIVE_ENDING = "ending_not_in_er_ir_re_oir"
    HYPHENATED_TOKEN = "hyphenated_token_needs_lemma_review"
    MULTIWORD_TOKEN = "multiword_token_needs_lemma_review"
    APOSTROPHE_TOKEN = "apostrophe_token_needs_lemma_review"
    NON_LETTER_SYMBOL = "non_letter_symbol_needs_lemma_review"
    MULTIPLE_GROUP_SUGGESTIONS = "multiple_group_suggestions"
