"""Tests for artifact-centric memory models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.memory.artifacts.models import ArtifactLineageNode, ArtifactRevision


class TestArtifactRevision:
    """Validate artifact revision model behavior."""

    def test_hash_payload_is_deterministic(self):
        """Equivalent payloads should produce the same hash."""
        payload_a = {"b": 2, "a": 1}
        payload_b = {"a": 1, "b": 2}

        assert ArtifactRevision.hash_payload(payload_a) == ArtifactRevision.hash_payload(payload_b)

    def test_revision_requires_positive_number(self):
        """Revision numbers must start at 1."""
        with pytest.raises(ValidationError):
            ArtifactRevision(
                revision_id="rev-1",
                artifact_id="artifact-1",
                revision_number=0,
                payload={},
                payload_hash="abc123",
            )


class TestArtifactLineageNode:
    """Validate lineage node schema."""

    def test_lineage_node_accepts_revision_entry(self):
        """A revision lineage node should validate with metadata."""
        node = ArtifactLineageNode(
            node_type="revision",
            node_id="rev-1",
            artifact_id="artifact-1",
            relation="HAS_REVISION",
            revision_id="rev-1",
            parent_id=None,
            timestamp=datetime.now(UTC),
            content="Draft revision",
            metadata={"revision_number": 1},
        )

        assert node.node_type == "revision"
        assert node.metadata["revision_number"] == 1

