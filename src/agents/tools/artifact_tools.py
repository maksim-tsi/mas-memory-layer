"""
Artifact lifecycle tools for agent access.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from src.agents.runtime import MASToolRuntime

if TYPE_CHECKING:
    from langchain_core.tools import ToolRuntime, tool
else:
    try:
        from langchain_core.tools import tool

        ToolRuntime = Any
    except ImportError:
        def tool(*args, **kwargs):
            def decorator(func):
                func.name = func.__name__
                func.description = func.__doc__ or ""
                func.args_schema = kwargs.get("args_schema")
                func.func = func
                return func

            if args and callable(args[0]):
                return decorator(args[0])
            return decorator

        ToolRuntime = Any


def _resolve_artifact_service(memory_system: Any) -> Any | None:
    """Resolve artifact service from either unified memory facade."""
    if memory_system is None:
        return None
    service = getattr(memory_system, "artifact_service", None)
    if service is not None:
        return service
    return getattr(memory_system, "artifacts", None)


class ArtifactSaveDraftInput(BaseModel):
    """Input schema for artifact_save_draft."""

    artifact_kind: str = Field(description="Generic artifact type label")
    payload: dict[str, Any] = Field(description="Opaque structured payload")
    artifact_id: str | None = Field(default=None, description="Existing artifact id for a new draft")
    summary: str | None = Field(default=None, description="Optional human-readable summary")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class ArtifactAttachFeedbackInput(BaseModel):
    """Input schema for artifact_attach_feedback."""

    artifact_id: str = Field(description="Artifact identifier")
    revision_id: str = Field(description="Target artifact revision identifier")
    feedback_type: str = Field(description="Feedback category, e.g. solver_iis or solver_success")
    source_system: str = Field(description="External system name")
    content: str = Field(description="Human-readable feedback content")
    structured_payload: dict[str, Any] | None = Field(
        default=None, description="Optional structured feedback payload"
    )
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class ArtifactCreateRevisionInput(BaseModel):
    """Input schema for artifact_create_revision."""

    artifact_id: str = Field(description="Artifact identifier")
    parent_revision_id: str = Field(description="Parent revision identifier")
    payload: dict[str, Any] = Field(description="Opaque revised payload")
    trigger_feedback_id: str | None = Field(
        default=None, description="Feedback id that triggered this revision"
    )
    summary: str | None = Field(default=None, description="Optional human-readable summary")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class ArtifactCommitFinalInput(BaseModel):
    """Input schema for artifact_commit_final."""

    artifact_id: str = Field(description="Artifact identifier")
    revision_id: str = Field(description="Feasible revision identifier")
    commit_reason: str | None = Field(default=None, description="Optional commit rationale")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class ArtifactGetLineageInput(BaseModel):
    """Input schema for artifact_get_lineage."""

    artifact_id: str = Field(description="Artifact identifier")
    revision_id: str | None = Field(default=None, description="Optional focal revision identifier")


@tool(args_schema=ArtifactSaveDraftInput)
async def artifact_save_draft(
    artifact_kind: str,
    payload: dict[str, Any],
    artifact_id: str | None = None,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
    runtime: ToolRuntime = None,
) -> str:
    """
    Save a draft artifact revision in working memory and lineage graph.
    """
    mas_runtime = MASToolRuntime(runtime)
    memory_system = mas_runtime.get_memory_system()
    artifact_service = _resolve_artifact_service(memory_system)
    if artifact_service is None:
        return "Error: Artifact service not available"

    session_id = mas_runtime.get_session_id()
    await mas_runtime.stream_status(f"Saving draft artifact ({artifact_kind})...")
    revision = await artifact_service.create_draft(
        artifact_kind=artifact_kind,
        payload=payload,
        artifact_id=artifact_id,
        session_id=session_id,
        summary=summary,
        metadata=metadata,
        created_by=mas_runtime.get_agent_id(),
    )
    return json.dumps(
        {
            "artifact_id": revision.artifact_id,
            "revision_id": revision.revision_id,
            "revision_number": revision.revision_number,
            "verification_state": revision.verification_state,
        },
        indent=2,
    )


@tool(args_schema=ArtifactAttachFeedbackInput)
async def artifact_attach_feedback(
    artifact_id: str,
    revision_id: str,
    feedback_type: str,
    source_system: str,
    content: str,
    structured_payload: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    runtime: ToolRuntime = None,
) -> str:
    """
    Attach external computational feedback to a specific artifact revision.
    """
    mas_runtime = MASToolRuntime(runtime)
    memory_system = mas_runtime.get_memory_system()
    artifact_service = _resolve_artifact_service(memory_system)
    if artifact_service is None:
        return "Error: Artifact service not available"

    await mas_runtime.stream_status(f"Attaching {feedback_type} feedback...")
    feedback = await artifact_service.attach_feedback(
        artifact_id=artifact_id,
        revision_id=revision_id,
        feedback_type=feedback_type,
        source_system=source_system,
        content=content,
        structured_payload=structured_payload,
        metadata=metadata,
    )
    return json.dumps({"feedback_id": feedback.feedback_id}, indent=2)


@tool(args_schema=ArtifactCreateRevisionInput)
async def artifact_create_revision(
    artifact_id: str,
    parent_revision_id: str,
    payload: dict[str, Any],
    trigger_feedback_id: str | None = None,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
    runtime: ToolRuntime = None,
) -> str:
    """
    Create a new artifact revision linked to a predecessor and optional feedback trigger.
    """
    mas_runtime = MASToolRuntime(runtime)
    memory_system = mas_runtime.get_memory_system()
    artifact_service = _resolve_artifact_service(memory_system)
    if artifact_service is None:
        return "Error: Artifact service not available"

    await mas_runtime.stream_status(f"Creating revision for artifact {artifact_id}...")
    revision = await artifact_service.create_revision(
        artifact_id=artifact_id,
        parent_revision_id=parent_revision_id,
        payload=payload,
        trigger_feedback_id=trigger_feedback_id,
        summary=summary,
        metadata=metadata,
        created_by=mas_runtime.get_agent_id(),
    )
    return json.dumps(
        {
            "artifact_id": revision.artifact_id,
            "revision_id": revision.revision_id,
            "revision_number": revision.revision_number,
            "trigger_feedback_id": revision.trigger_feedback_id,
        },
        indent=2,
    )


@tool(args_schema=ArtifactCommitFinalInput)
async def artifact_commit_final(
    artifact_id: str,
    revision_id: str,
    commit_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    runtime: ToolRuntime = None,
) -> str:
    """
    Commit a feasible artifact revision into semantic memory with lineage preserved.
    """
    mas_runtime = MASToolRuntime(runtime)
    memory_system = mas_runtime.get_memory_system()
    artifact_service = _resolve_artifact_service(memory_system)
    if artifact_service is None:
        return "Error: Artifact service not available"

    await mas_runtime.stream_status(f"Committing final artifact revision {revision_id}...")
    commit = await artifact_service.commit_final(
        artifact_id=artifact_id,
        revision_id=revision_id,
        commit_reason=commit_reason,
        metadata=metadata,
    )
    return json.dumps(
        {
            "commit_id": commit.commit_id,
            "knowledge_id": commit.knowledge_id,
            "artifact_id": commit.artifact_id,
            "revision_id": commit.revision_id,
        },
        indent=2,
    )


@tool(args_schema=ArtifactGetLineageInput)
async def artifact_get_lineage(
    artifact_id: str,
    revision_id: str | None = None,
    runtime: ToolRuntime = None,
) -> str:
    """
    Retrieve the ordered lineage of revisions, feedback, commits, and knowledge links.
    """
    mas_runtime = MASToolRuntime(runtime)
    memory_system = mas_runtime.get_memory_system()
    artifact_service = _resolve_artifact_service(memory_system)
    if artifact_service is None:
        return "Error: Artifact service not available"

    await mas_runtime.stream_status(f"Retrieving lineage for artifact {artifact_id}...")
    lineage = await artifact_service.get_lineage(artifact_id=artifact_id, revision_id=revision_id)
    return json.dumps(lineage.model_dump(mode="json"), indent=2)


ARTIFACT_TOOLS = [
    artifact_save_draft,
    artifact_attach_feedback,
    artifact_create_revision,
    artifact_commit_final,
    artifact_get_lineage,
]

__all__ = [
    "ARTIFACT_TOOLS",
    "ArtifactAttachFeedbackInput",
    "ArtifactCommitFinalInput",
    "ArtifactCreateRevisionInput",
    "ArtifactGetLineageInput",
    "ArtifactSaveDraftInput",
    "artifact_attach_feedback",
    "artifact_commit_final",
    "artifact_create_revision",
    "artifact_get_lineage",
    "artifact_save_draft",
]
