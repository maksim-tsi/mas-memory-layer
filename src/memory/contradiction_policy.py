"""Deterministic contradiction and supersession policy helpers.

This module stays above the storage layer. It marks or filters fact objects
using metadata so historical facts remain auditable.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import ClassVar

from src.memory.models import Fact

CONTRADICTION_POLICY_MODES = {"off", "metadata_only", "suppress_superseded"}


@dataclass
class ContradictionAssessment:
    """Policy decision for one fact in a contradiction/supersession group."""

    mode: str
    decision: str = "STORE"
    contradiction_candidate: bool = False
    conflict_group_id: str | None = None
    supersedes_fact_ids: list[str] = field(default_factory=list)
    superseded_by_fact_id: str | None = None
    detector_confidence: float = 0.0
    reason: str = "no_contradiction_signal"
    negated_terms: list[str] = field(default_factory=list)
    replacement_terms: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "decision": self.decision,
            "contradiction_candidate": self.contradiction_candidate,
            "conflict_group_id": self.conflict_group_id,
            "supersedes_fact_ids": self.supersedes_fact_ids,
            "superseded_by_fact_id": self.superseded_by_fact_id,
            "detector_confidence": round(self.detector_confidence, 4),
            "reason": self.reason,
            "negated_terms": self.negated_terms,
            "replacement_terms": self.replacement_terms,
        }


class ContradictionPolicy:
    """Conservative explicit-correction detector for L2 fact promotion."""

    UPDATE_TERMS: ClassVar[set[str]] = {
        "actually",
        "correction",
        "corrected",
        "changed",
        "instead",
        "no longer",
        "updated",
        "reroute",
        "rerouted",
    }
    NEGATED_TERM_PATTERNS: ClassVar[tuple[re.Pattern[str], ...]] = (
        re.compile(r"\bnot\s+([a-z0-9][a-z0-9 -]*?)(?:[.,;]|$)"),
        re.compile(r"\binstead of\s+([a-z0-9][a-z0-9 -]*?)(?:[.,;]|$)"),
        re.compile(r"\bno longer\s+(?:uses?|goes to|scheduled for|routed to|at)?\s*([a-z0-9][a-z0-9 -]*?)(?:[.,;]|$)"),
    )
    REPLACEMENT_TERM_PATTERNS: ClassVar[tuple[re.Pattern[str], ...]] = (
        re.compile(r"\b(?:rerouted|routed|changed|updated)\s+to\s+([a-z0-9][a-z0-9 -]*?)(?:[.,;]|\s+not\b|\s+instead\b|$)"),
        re.compile(r"\binstead\s+to\s+([a-z0-9][a-z0-9 -]*?)(?:[.,;]|$)"),
    )
    STOPWORDS: ClassVar[set[str]] = {
        "a",
        "an",
        "as",
        "at",
        "for",
        "from",
        "is",
        "it",
        "now",
        "of",
        "on",
        "the",
        "this",
        "to",
    }

    def __init__(self, mode: str = "off") -> None:
        if mode not in CONTRADICTION_POLICY_MODES:
            raise ValueError(
                "contradiction_policy_mode must be one of "
                f"{sorted(CONTRADICTION_POLICY_MODES)}, got {mode!r}"
            )
        self.mode = mode

    def assess(
        self,
        facts: list[Fact],
        *,
        existing_facts: list[Fact] | None = None,
    ) -> dict[str, ContradictionAssessment]:
        """Assess a batch of candidate facts against earlier/session facts."""
        if self.mode == "off":
            return {}

        assessments = {
            fact.fact_id: ContradictionAssessment(mode=self.mode) for fact in facts
        }
        existing = existing_facts or []
        all_prior: list[Fact] = [*existing]

        for fact in facts:
            assessment = assessments[fact.fact_id]
            content = self._normalize(fact.content)
            update_candidate = any(term in content for term in self.UPDATE_TERMS)
            negated_terms = self._extract_terms(content, self.NEGATED_TERM_PATTERNS)
            replacement_terms = self._extract_terms(content, self.REPLACEMENT_TERM_PATTERNS)

            if update_candidate:
                assessment.contradiction_candidate = True
                assessment.negated_terms = negated_terms
                assessment.replacement_terms = replacement_terms
                assessment.detector_confidence = 0.55
                assessment.reason = "explicit_update_no_match"

            superseded = [
                prior
                for prior in all_prior
                if negated_terms and self._matches_any_term(prior.content, negated_terms)
            ]
            if superseded:
                group_id = self._group_id(fact, negated_terms, replacement_terms)
                assessment.conflict_group_id = group_id
                assessment.supersedes_fact_ids = [prior.fact_id for prior in superseded]
                assessment.detector_confidence = 0.9
                assessment.reason = "explicit_update_supersedes_prior_fact"

                for prior in superseded:
                    if prior.fact_id in assessments:
                        prior_assessment = assessments[prior.fact_id]
                        prior_assessment.decision = (
                            "SUPPRESS" if self.mode == "suppress_superseded" else "ANNOTATE"
                        )
                        prior_assessment.contradiction_candidate = True
                        prior_assessment.conflict_group_id = group_id
                        prior_assessment.superseded_by_fact_id = fact.fact_id
                        prior_assessment.detector_confidence = 0.9
                        prior_assessment.reason = "superseded_by_explicit_update"
                        prior_assessment.negated_terms = negated_terms
                        prior_assessment.replacement_terms = replacement_terms

            all_prior.append(fact)

        return {
            fact_id: assessment
            for fact_id, assessment in assessments.items()
            if assessment.contradiction_candidate
            or assessment.supersedes_fact_ids
            or assessment.superseded_by_fact_id
        }

    @classmethod
    def filter_superseded(cls, facts: list[Fact], *, mode: str) -> list[Fact]:
        """Omit facts superseded under the active suppression policy."""
        if mode != "suppress_superseded":
            return facts

        suppressed_ids: set[str] = set()
        for fact in facts:
            metadata = cls._metadata_for_fact(fact)
            if metadata.get("mode") != "suppress_superseded":
                continue
            if metadata.get("decision") == "SUPPRESS":
                suppressed_ids.add(fact.fact_id)
            for superseded_id in metadata.get("supersedes_fact_ids") or []:
                suppressed_ids.add(str(superseded_id))

        return [fact for fact in facts if fact.fact_id not in suppressed_ids]

    @classmethod
    def _metadata_for_fact(cls, fact: Fact) -> dict[str, object]:
        metadata = fact.metadata or {}
        value = metadata.get("contradiction_policy")
        return value if isinstance(value, dict) else {}

    @classmethod
    def _normalize(cls, value: str) -> str:
        return " ".join(value.lower().split())

    @classmethod
    def _extract_terms(
        cls, content: str, patterns: tuple[re.Pattern[str], ...]
    ) -> list[str]:
        terms: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(content):
                term = cls._clean_term(match.group(1))
                if term:
                    terms.append(term)
        return sorted(set(terms))

    @classmethod
    def _clean_term(cls, value: str) -> str:
        words = [
            word
            for word in re.split(r"\s+", value.strip(" .,:;"))
            if word and word not in cls.STOPWORDS
        ]
        return " ".join(words[:3])

    @classmethod
    def _matches_any_term(cls, content: str, terms: list[str]) -> bool:
        normalized = cls._normalize(content)
        return any(cls._term_in_content(term, normalized) for term in terms)

    @classmethod
    def _term_in_content(cls, term: str, normalized_content: str) -> bool:
        if not term:
            return False
        return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", normalized_content) is not None

    @staticmethod
    def _group_id(fact: Fact, negated_terms: list[str], replacement_terms: list[str]) -> str:
        seed = "|".join([fact.session_id, *negated_terms, *replacement_terms])
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
        return f"contradiction-{digest}"
