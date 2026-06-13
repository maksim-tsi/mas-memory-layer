"""Tests for artifact-centric memory service."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.memory.artifacts.models import Artifact, ArtifactRevision
from src.memory.artifacts.service import ArtifactService


@pytest.fixture
def mock_repository():
    """Create a repository mock with async methods."""
    repo = AsyncMock()
    repo.get_artifact.return_value = None
    repo.get_next_revision_number.return_value = 2
    repo.get_revision.return_value = None
    repo.store_final_knowledge_projection.return_value = None
    repo.get_lineage.return_value = AsyncMock()
    return repo


@pytest.mark.asyncio
class TestArtifactService:
    """Artifact service behavior."""

    async def test_create_draft_creates_first_revision(self, mock_repository):
        """Creating a draft should create artifact root and revision 1."""
        service = ArtifactService(mock_repository)

        revision = await service.create_draft(
            artifact_kind="routing_payload",
            payload={"route": "A-B"},
            session_id="session-1",
            summary="Initial draft",
        )

        assert revision.revision_number == 1
        assert revision.verification_state == "unverified"
        mock_repository.create_artifact.assert_awaited_once()
        mock_repository.store_revision.assert_awaited_once()

    async def test_attach_infeasible_feedback_marks_revision_failed(self, mock_repository):
        """Solver IIS feedback should mark a revision infeasible."""
        artifact = Artifact(
            artifact_id="artifact-1",
            artifact_kind="routing_payload",
            session_id="session-1",
        )
        revision = ArtifactRevision(
            revision_id="rev-1",
            artifact_id="artifact-1",
            revision_number=1,
            payload={"route": "A-B"},
            payload_hash=ArtifactRevision.hash_payload({"route": "A-B"}),
        )
        mock_repository.get_artifact.return_value = artifact
        mock_repository.get_revision.return_value = revision

        service = ArtifactService(mock_repository)
        feedback = await service.attach_feedback(
            artifact_id="artifact-1",
            revision_id="rev-1",
            feedback_type="solver_iis",
            source_system="scip",
            content="capacity infeasible",
        )

        assert feedback.feedback_type == "solver_iis"
        mock_repository.update_revision_verification.assert_awaited_once()
        mock_repository.update_artifact.assert_awaited_once()

    async def test_commit_final_requires_feasible_revision(self, mock_repository):
        """Non-feasible revisions must not be committed."""
        artifact = Artifact(
            artifact_id="artifact-1",
            artifact_kind="routing_payload",
            session_id="session-1",
        )
        revision = ArtifactRevision(
            revision_id="rev-1",
            artifact_id="artifact-1",
            revision_number=1,
            payload={"route": "A-B"},
            payload_hash=ArtifactRevision.hash_payload({"route": "A-B"}),
            verification_state="unverified",
        )
        mock_repository.get_artifact.return_value = artifact
        mock_repository.get_revision.return_value = revision

        service = ArtifactService(mock_repository)

        with pytest.raises(ValueError, match="not feasible"):
            await service.commit_final(artifact_id="artifact-1", revision_id="rev-1")

