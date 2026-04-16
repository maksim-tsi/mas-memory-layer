from __future__ import annotations

from pathlib import Path

import pytest

from src.skills.loader import (
    SkillLoadError,
    filter_tools_by_allowed_names,
    list_skill_slugs,
    load_skill,
)


def test_list_skill_slugs_includes_runtime_skills() -> None:
    slugs = list_skill_slugs()
    assert "context-block-retrieval" in slugs
    assert "skill-selection" in slugs
    assert all(not s.startswith("dev/") for s in slugs)


def test_list_skill_slugs_can_include_dev_skills() -> None:
    slugs = list_skill_slugs(include_dev=True)
    assert "dev/skillbuilder" in slugs


def test_load_skill_parses_manifest_and_body() -> None:
    pkg = load_skill("context-block-retrieval")
    assert pkg.namespace == "runtime"
    assert pkg.slug == "context-block-retrieval"
    assert pkg.path.name == "SKILL.md"
    assert pkg.manifest.name
    assert pkg.manifest.description
    assert "allowed-tools" not in pkg.body
    assert "get_context_block" in pkg.manifest.allowed_tools


def test_load_dev_skill() -> None:
    pkg = load_skill("dev/skillbuilder")
    assert pkg.namespace == "dev"
    assert pkg.slug == "skillbuilder"
    assert pkg.manifest.name.startswith("Skill Builder")


def test_load_skill_invalid_slug_raises() -> None:
    with pytest.raises(SkillLoadError):
        load_skill("bad/slug")


def test_filter_tools_by_allowed_names_filters_on_tool_name_attr() -> None:
    class Tool:
        def __init__(self, name: str):
            self.name = name

    tools = [Tool("a"), Tool("b"), Tool("c")]
    filtered = filter_tools_by_allowed_names(tools, ["b", "c"])
    assert [t.name for t in filtered] == ["b", "c"]


def test_filter_tools_by_allowed_names_empty_allowed_means_none() -> None:
    tools = [lambda: None]
    assert filter_tools_by_allowed_names(tools, []) == []


def test_load_skill_with_repo_root_override(tmp_path: Path) -> None:
    # Minimal fake skill tree
    skills_dir = tmp_path / "skills" / "demo-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        "---\nname: \"Demo\"\ndescription: \"Demo\"\nallowed-tools:\n  - \"t\"\n---\n\nBody\n",
        encoding="utf-8",
    )

    pkg = load_skill("demo-skill", repo_root=tmp_path)
    assert pkg.slug == "demo-skill"
    assert pkg.manifest.allowed_tools == ("t",)
