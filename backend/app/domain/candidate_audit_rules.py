"""Declarative, versioned rules used by the candidate-infinitive audit.

The auditor implements reusable operations. Suffix expectations and lexeme-specific
exceptions are data, so language decisions do not accumulate as code patches.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from app.domain.candidate_lexicon import normalize_candidate_form
from app.domain.verb_contracts import ContractModel, VerbGroup

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RULES_PATH = ROOT / "data" / "catalogs" / "candidate-audit-rules.json"


class GroupSuffixException(ContractModel):
    candidate_form: str = Field(min_length=2, max_length=100)
    group_id: VerbGroup
    accepted_suffixes: list[str] = Field(min_length=1, max_length=10)
    rationale: str = Field(min_length=10, max_length=500)

    @model_validator(mode="after")
    def validate_exception(self) -> "GroupSuffixException":
        if self.candidate_form != normalize_candidate_form(self.candidate_form):
            raise ValueError("candidate_form must be normalized lowercase NFC")
        if len(self.accepted_suffixes) != len(set(self.accepted_suffixes)):
            raise ValueError("accepted_suffixes must not contain duplicates")
        if not any(self.candidate_form.endswith(suffix) for suffix in self.accepted_suffixes):
            raise ValueError("candidate_form must end with at least one accepted_suffix")
        return self


class CandidateAuditRules(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    recognized_infinitive_suffixes: list[str] = Field(min_length=1)
    equivalent_suffix_classes: dict[str, list[str]]
    group_expected_suffix_classes: dict[VerbGroup, list[str]]
    group_suffix_exceptions: list[GroupSuffixException] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rules(self) -> "CandidateAuditRules":
        if len(self.recognized_infinitive_suffixes) != len(set(self.recognized_infinitive_suffixes)):
            raise ValueError("recognized_infinitive_suffixes must not contain duplicates")
        for group in VerbGroup:
            if group not in self.group_expected_suffix_classes or not self.group_expected_suffix_classes[group]:
                raise ValueError(f"group_expected_suffix_classes must define a non-empty list for {group.value}")
        for class_name, members in self.equivalent_suffix_classes.items():
            if not class_name or not members or len(members) != len(set(members)):
                raise ValueError(f"Invalid equivalent suffix class: {class_name!r}")
            if any(member not in self.recognized_infinitive_suffixes for member in members):
                raise ValueError(f"Equivalent suffix class {class_name!r} contains an unrecognized suffix")
        for group, expected_items in self.group_expected_suffix_classes.items():
            for item in expected_items:
                if item not in self.equivalent_suffix_classes and item not in self.recognized_infinitive_suffixes:
                    raise ValueError(
                        f"Unknown expected suffix or suffix class {item!r} for group {group.value}"
                    )
        exception_keys = [(item.candidate_form, item.group_id) for item in self.group_suffix_exceptions]
        if len(exception_keys) != len(set(exception_keys)):
            raise ValueError("Only one suffix exception is allowed per candidate_form/group_id")
        return self


@lru_cache(maxsize=4)
def load_candidate_audit_rules(path_string: str | None = None) -> CandidateAuditRules:
    """Load and cache validated audit rules from a JSON registry."""
    path = Path(path_string) if path_string else DEFAULT_RULES_PATH
    if not path.exists():
        raise FileNotFoundError(f"Candidate audit rules file is missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read candidate audit rules at {path}: {exc}") from exc
    return CandidateAuditRules.model_validate(data)


def group_suffix_is_compatible(
    candidate_form: str,
    group_id: VerbGroup | str,
    rules: CandidateAuditRules,
) -> bool:
    """Check the declared suffix policy and data-driven exceptions for one group."""
    group = group_id if isinstance(group_id, VerbGroup) else VerbGroup(group_id)
    normalized = unicodedata.normalize("NFC", candidate_form).strip().lower()
    expected_items = rules.group_expected_suffix_classes[group]
    expected_suffixes = [
        suffix
        for item in expected_items
        for suffix in rules.equivalent_suffix_classes.get(item, [item])
    ]
    if any(normalized.endswith(suffix) for suffix in expected_suffixes):
        return True
    return any(
        exception.candidate_form == normalized
        and exception.group_id == group
        and any(normalized.endswith(suffix) for suffix in exception.accepted_suffixes)
        for exception in rules.group_suffix_exceptions
    )


def has_recognized_infinitive_ending(candidate_form: str, rules: CandidateAuditRules) -> bool:
    """Return only whether the ending is known to the audit rules, not whether
    the token is actually an infinitive.
    """
    normalized = unicodedata.normalize("NFC", candidate_form).strip().lower()
    return any(normalized.endswith(suffix) for suffix in rules.recognized_infinitive_suffixes)
