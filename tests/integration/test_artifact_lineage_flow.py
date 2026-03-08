"""Focused integration-style test for artifact lineage flow."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from src.memory.artifacts.models import (
    Artifact,
    ArtifactCommit,
    ArtifactFeedback,
    ArtifactLineageNode,
    ArtifactLineageQuery,
    ArtifactLineageResult,
    ArtifactRevision,
)
from src.memory.artifacts.service import ArtifactService


@dataclass
class InMemoryArtifactRepository:
    """Small in-memory repository for end-to-end service validation."""

    artifacts: dict[str, Artifact] = field(default_factory=dict)
    revisions: dict[str, ArtifactRevision] = field(default_factory=dict)
    feedbacks: dict[str, ArtifactFeedback] = field(default_factory=dict)
    commits: dict[str, ArtifactCommit] = field(default_factory=dict)
    linked_knowledge: dict[str, str] = field(default_factory=dict)

    async def create_artifact(self, artifact: Artifact) -> None:
        self.artifacts[artifact.artifact_id] = artifact

    async def update_artifact(
        self,
        artifact_id: str,
        *,
        status: str,
        current_revision_id: str | None,
        session_id: str,
        metadata: dict | None = None,
    ) -> None:
        artifact = self.artifacts[artifact_id]
        artifact.status = status
        artifact.current_revision_id = current_revision_id
        artifact.metadata = metadata or artifact.metadata
        self.artifacts[artifact_id] = artifact

    async def get_artifact(self, artifact_id: str) -> Artifact | None:
        return self.artifacts.get(artifact_id)

    async def store_revision(self, artifact: Artifact, revision: ArtifactRevision) -> None:
        self.revisions[revision.revision_id] = revision

    async def get_revision(self, revision_id: str) -> ArtifactRevision | None:
        return self.revisions.get(revision_id)

    async def get_next_revision_number(self, artifact_id: str) -> int:
        numbers = [
            revision.revision_number
            for revision in self.revisions.values()
            if revision.artifact_id == artifact_id
        ]
        return (max(numbers) if numbers else 0) + 1

    async def update_revision_verification(
        self,
        revision_id: str,
        verification_state: str,
        *,
        tier_state: str | None = None,
        trigger_feedback_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        revision = self.revisions[revision_id]
        revision.verification_state = verification_state
        if tier_state is not None:
            revision.tier_state = tier_state
        if trigger_feedback_id is not None:
            revision.trigger_feedback_id = trigger_feedback_id
        self.revisions[revision_id] = revision

    async def store_feedback(self, artifact: Artifact, feedback: ArtifactFeedback) -> None:
        self.feedbacks[feedback.feedback_id] = feedback

    async def link_revision_to_feedback(
        self, revision_id: str, feedback_id: str, *, session_id: str | None = None
    ) -> None:
        revision = self.revisions[revision_id]
        revision.trigger_feedback_id = feedback_id
        self.revisions[revision_id] = revision

    async def store_final_knowledge_projection(
        self,
        artifact: Artifact,
        revision: ArtifactRevision,
        commit: ArtifactCommit,
    ):
        commit.knowledge_id = f"know-{commit.commit_id}"

        class KnowledgeProjection:
            knowledge_id = f"know-{commit.commit_id}"

        self.linked_knowledge[revision.revision_id] = KnowledgeProjection.knowledge_id
        return KnowledgeProjection()

    async def store_commit(
        self,
        artifact: Artifact,
        revision: ArtifactRevision,
        commit: ArtifactCommit,
        knowledge=None,
    ) -> None:
        self.commits[commit.commit_id] = commit

    async def get_lineage(self, query_model: ArtifactLineageQuery) -> ArtifactLineageResult:
        nodes: list[ArtifactLineageNode] = []
        artifact = self.artifacts[query_model.artifact_id]
        for revision in sorted(
            [r for r in self.revisions.values() if r.artifact_id == query_model.artifact_id],
            key=lambda item: item.revision_number,
        ):
            nodes.append(
                ArtifactLineageNode(
                    node_type="revision",
                    node_id=revision.revision_id,
                    artifact_id=query_model.artifact_id,
                    relation="HAS_REVISION",
                    revision_id=revision.revision_id,
                    parent_id=revision.parent_revision_id,
                    content=revision.summary,
                    metadata={"revision_number": revision.revision_number},
                )
            )
            for feedback in self.feedbacks.values():
                if feedback.revision_id == revision.revision_id:
                    nodes.append(
                        ArtifactLineageNode(
                            node_type="feedback",
                            node_id=feedback.feedback_id,
                            artifact_id=query_model.artifact_id,
                            relation="APPLIES_TO",
                            revision_id=revision.revision_id,
                            parent_id=revision.revision_id,
                            content=feedback.content,
                            metadata={"feedback_type": feedback.feedback_type},
                        )
                    )
            if revision.revision_id in self.linked_knowledge:
                nodes.append(
                    ArtifactLineageNode(
                        node_type="knowledge",
                        node_id=self.linked_knowledge[revision.revision_id],
                        artifact_id=query_model.artifact_id,
                        relation="DERIVED_FROM_ARTIFACT",
                        revision_id=revision.revision_id,
                        parent_id=revision.revision_id,
                    )
                )
        for commit in self.commits.values():
            if commit.artifact_id == query_model.artifact_id:
                nodes.append(
                    ArtifactLineageNode(
                        node_type="commit",
                        node_id=commit.commit_id,
                        artifact_id=query_model.artifact_id,
                        relation="COMMITS",
                        revision_id=commit.revision_id,
                        parent_id=commit.revision_id,
                        content=commit.commit_reason,
                    )
                )
        return ArtifactLineageResult(
            artifact_id=query_model.artifact_id,
            current_revision_id=artifact.current_revision_id,
            nodes=nodes,
        )


@pytest.mark.asyncio
async def test_artifact_lineage_flow():
    """Artifact lineage flow should preserve v1 -> IIS -> v2 -> commit history."""
    repository = InMemoryArtifactRepository()
    service = ArtifactService(repository)

    v1 = await service.create_draft(
        artifact_kind="routing_payload",
        payload={"route": "A-B", "capacity": 10},
        session_id="session-1",
        summary="Initial routing draft",
    )
    feedback = await service.attach_feedback(
        artifact_id=v1.artifact_id,
        revision_id=v1.revision_id,
        feedback_type="solver_iis",
        source_system="scip",
        content="Capacity constraint infeasible",
    )
    v2 = await service.create_revision(
        artifact_id=v1.artifact_id,
        parent_revision_id=v1.revision_id,
        payload={"route": "A-C", "capacity": 12},
        trigger_feedback_id=feedback.feedback_id,
        summary="Adjusted route after IIS analysis",
    )
    await service.attach_feedback(
        artifact_id=v1.artifact_id,
        revision_id=v2.revision_id,
        feedback_type="solver_success",
        source_system="scip",
        content="Feasible solution found",
    )
    commit = await service.commit_final(
        artifact_id=v1.artifact_id,
        revision_id=v2.revision_id,
        commit_reason="Solver validated final artifact",
    )
    lineage = await service.get_lineage(artifact_id=v1.artifact_id)

    assert v1.revision_id != v2.revision_id
    assert commit.knowledge_id is not None
    assert any(node.node_id == v1.revision_id for node in lineage.nodes)
    assert any(node.node_id == feedback.feedback_id for node in lineage.nodes)
    assert any(node.node_id == v2.revision_id for node in lineage.nodes)
    assert any(node.node_id == commit.commit_id for node in lineage.nodes)
    assert any(node.node_type == "knowledge" for node in lineage.nodes)
