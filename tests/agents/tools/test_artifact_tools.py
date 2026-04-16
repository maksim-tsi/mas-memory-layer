"""Tests for artifact lifecycle tools."""

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from src.agents.tools.artifact_tools import (
    ArtifactAttachFeedbackInput,
    ArtifactCommitFinalInput,
    ArtifactCreateRevisionInput,
    ArtifactGetLineageInput,
    ArtifactSaveDraftInput,
    artifact_attach_feedback,
    artifact_commit_final,
    artifact_create_revision,
    artifact_get_lineage,
    artifact_save_draft,
)
from src.memory.artifacts.models import (
    ArtifactCommit,
    ArtifactFeedback,
    ArtifactLineageResult,
    ArtifactRevision,
)


class TestArtifactToolMetadata:
    """Metadata sanity checks."""

    def test_artifact_save_draft_metadata(self):
        assert artifact_save_draft.name == "artifact_save_draft"
        assert artifact_save_draft.args_schema == ArtifactSaveDraftInput

    def test_artifact_attach_feedback_metadata(self):
        assert artifact_attach_feedback.name == "artifact_attach_feedback"
        assert artifact_attach_feedback.args_schema == ArtifactAttachFeedbackInput

    def test_artifact_create_revision_metadata(self):
        assert artifact_create_revision.name == "artifact_create_revision"
        assert artifact_create_revision.args_schema == ArtifactCreateRevisionInput

    def test_artifact_commit_final_metadata(self):
        assert artifact_commit_final.name == "artifact_commit_final"
        assert artifact_commit_final.args_schema == ArtifactCommitFinalInput

    def test_artifact_get_lineage_metadata(self):
        assert artifact_get_lineage.name == "artifact_get_lineage"
        assert artifact_get_lineage.args_schema == ArtifactGetLineageInput


@pytest.mark.asyncio
class TestArtifactTools:
    """Behavior checks with mocked runtime context."""

    async def test_artifact_save_draft_error_without_service(self):
        @dataclass
        class MockContext:
            session_id: str = "session-1"
            memory_system: object = None

        @dataclass
        class MockToolRuntime:
            context: object
            state: dict

        runtime = MockToolRuntime(context=MockContext(), state={})
        result = await artifact_save_draft.coroutine(
            artifact_kind="routing_payload",
            payload={"route": "A-B"},
            runtime=runtime,
        )

        assert "Error: Artifact service not available" in result

    async def test_artifact_commit_final_success(self):
        revision = ArtifactRevision(
            revision_id="rev-2",
            artifact_id="artifact-1",
            revision_number=2,
            payload={"route": "B-C"},
            payload_hash=ArtifactRevision.hash_payload({"route": "B-C"}),
            verification_state="feasible",
        )
        service = AsyncMock()
        service.create_draft = AsyncMock(return_value=revision)
        service.commit_final = AsyncMock(
            return_value=ArtifactCommit(
                commit_id="commit-1",
                artifact_id="artifact-1",
                revision_id="rev-2",
                knowledge_id="know-1",
            )
        )
        service.attach_feedback = AsyncMock(
            return_value=ArtifactFeedback(
                feedback_id="feedback-1",
                artifact_id="artifact-1",
                revision_id="rev-1",
                feedback_type="solver_iis",
                source_system="scip",
                content="capacity infeasible",
            )
        )
        service.create_revision = AsyncMock(return_value=revision)
        service.get_lineage = AsyncMock(
            return_value=ArtifactLineageResult(artifact_id="artifact-1", current_revision_id="rev-2")
        )

        @dataclass
        class MockContext:
            session_id: str = "session-1"
            agent_id: str = "agent-1"
            memory_system: object = None

        @dataclass
        class MockToolRuntime:
            context: object
            state: dict

            async def stream_status(self, _status: str) -> None:
                return None

        memory_system = type("MemorySystem", (), {"artifact_service": service})()
        runtime = MockToolRuntime(
            context=MockContext(memory_system=memory_system),
            state={},
        )
        result = await artifact_commit_final.coroutine(
            artifact_id="artifact-1",
            revision_id="rev-2",
            runtime=runtime,
        )

        assert '"commit_id": "commit-1"' in result
        service.commit_final.assert_awaited_once()
