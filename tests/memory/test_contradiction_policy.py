from src.memory.contradiction_policy import ContradictionPolicy
from src.memory.models import Fact, FactCategory, FactType


def _fact(fact_id: str, content: str) -> Fact:
    return Fact(
        fact_id=fact_id,
        session_id="session-1",
        content=content,
        ciar_score=0.8,
        certainty=0.9,
        impact=0.9,
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
    )


def test_off_mode_returns_no_assessments():
    policy = ContradictionPolicy("off")

    assessments = policy.assess(
        [
            _fact("old", "The shipment was scheduled for Oakland."),
            _fact("new", "Correction: it is now rerouted to Los Angeles, not Oakland."),
        ]
    )

    assert assessments == {}


def test_suppress_superseded_marks_old_fact_and_current_fact():
    policy = ContradictionPolicy("suppress_superseded")

    assessments = policy.assess(
        [
            _fact("old", "The shipment was scheduled for Oakland."),
            _fact("new", "Correction: it is now rerouted to Los Angeles, not Oakland."),
        ]
    )

    assert assessments["old"].decision == "SUPPRESS"
    assert assessments["old"].superseded_by_fact_id == "new"
    assert assessments["new"].decision == "STORE"
    assert assessments["new"].supersedes_fact_ids == ["old"]
    assert assessments["new"].negated_terms == ["oakland"]
    assert assessments["new"].replacement_terms == ["los angeles"]


def test_metadata_only_marks_conflict_without_suppression():
    policy = ContradictionPolicy("metadata_only")

    assessments = policy.assess(
        [
            _fact("old", "The shipment was scheduled for Oakland."),
            _fact("new", "Correction: it is now rerouted to Los Angeles, not Oakland."),
        ]
    )

    assert assessments["old"].decision == "ANNOTATE"
    assert assessments["new"].supersedes_fact_ids == ["old"]


def test_instead_of_phrase_marks_superseded_fact():
    policy = ContradictionPolicy("suppress_superseded")

    assessments = policy.assess(
        [
            _fact("old", "The shipment was scheduled for Oakland."),
            _fact("new", "The shipment is now rerouted to Los Angeles instead of Oakland."),
        ]
    )

    assert assessments["old"].decision == "SUPPRESS"
    assert assessments["new"].negated_terms == ["oakland"]
    assert assessments["new"].replacement_terms == ["los angeles"]


def test_ambiguous_update_is_not_suppressed_without_prior_match():
    policy = ContradictionPolicy("suppress_superseded")

    assessments = policy.assess(
        [
            _fact("old", "The shipment was scheduled for Oakland."),
            _fact("new", "Correction: the route changed today."),
        ]
    )

    assert "old" not in assessments
    assert assessments["new"].decision == "STORE"
    assert assessments["new"].reason == "explicit_update_no_match"


def test_filter_superseded_only_applies_to_suppress_mode():
    old = _fact("old", "The shipment was scheduled for Oakland.")
    new = _fact("new", "Correction: it is now rerouted to Los Angeles, not Oakland.")
    new.metadata["contradiction_policy"] = {
        "mode": "suppress_superseded",
        "decision": "STORE",
        "supersedes_fact_ids": ["old"],
    }

    assert ContradictionPolicy.filter_superseded([old, new], mode="metadata_only") == [
        old,
        new,
    ]
    assert ContradictionPolicy.filter_superseded([old, new], mode="suppress_superseded") == [
        new
    ]
