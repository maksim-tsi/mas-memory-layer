"""Minimal skills loader (v1).

Goals:
- Dependency-free frontmatter parsing (no PyYAML required).
- Progressive disclosure: list skills, load one, filter tools by `allowed-tools`.

Skills live in the repository root:
- runtime skills: `skills/<slug>/SKILL.md`
- dev-time skills: `skills/dev/<slug>/SKILL.md`
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SkillLoadError(RuntimeError):
    """Raised when a skill cannot be located or parsed."""


@dataclass(frozen=True, slots=True)
class SkillManifest:
    """Parsed skill metadata from YAML frontmatter."""

    name: str
    description: str
    version: str | None
    compatibility: str | None
    allowed_tools: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SkillPackage:
    """Loaded skill manifest + markdown body."""

    slug: str
    namespace: str
    path: Path
    manifest: SkillManifest
    body: str


def _repo_root(start: Path | None = None) -> Path:
    """Resolve repository root (best-effort) starting from this file or an override."""
    if start is not None:
        return start
    return Path(__file__).resolve().parents[2]


def _skills_root(repo_root: Path) -> Path:
    return repo_root / "skills"


def list_skill_slugs(*, repo_root: Path | None = None, include_dev: bool = False) -> list[str]:
    """List available skill slugs.

    Args:
        repo_root: Repo root path override (defaults to inferred repo root).
        include_dev: Include dev-time skills under `skills/dev/`.

    Returns:
        Sorted list of slugs. Dev skills are returned with `dev/<slug>` prefix.
    """
    root = _skills_root(_repo_root(repo_root))
    slugs: list[str] = []

    # Runtime skills: skills/<slug>/SKILL.md
    if root.exists():
        for path in root.glob("*/SKILL.md"):
            if not path.is_file():
                continue
            slug = path.parent.name
            if slug in {"_template", "dev"}:
                continue
            slugs.append(slug)

        if include_dev:
            dev_root = root / "dev"
            if dev_root.exists():
                for path in dev_root.glob("*/SKILL.md"):
                    if not path.is_file():
                        continue
                    slugs.append(f"dev/{path.parent.name}")

    return sorted(slugs)


def load_skill(
    slug: str, *, repo_root: Path | None = None, namespace: str | None = None
) -> SkillPackage:
    """Load a skill from disk.

    Args:
        slug: Skill slug. Can be `dev/<slug>` or a runtime skill slug.
        repo_root: Repo root path override.
        namespace: Optional namespace override (`runtime` or `dev`). If omitted, inferred from slug.

    Returns:
        SkillPackage containing manifest and markdown body.

    Raises:
        SkillLoadError: if the file is missing or frontmatter is invalid.
    """
    repo = _repo_root(repo_root)
    skills_root = _skills_root(repo)

    inferred_namespace = "dev" if slug.startswith("dev/") else "runtime"
    ns = namespace or inferred_namespace

    if ns not in {"runtime", "dev"}:
        raise SkillLoadError(f"Invalid namespace: {ns!r}")

    clean_slug = slug.removeprefix("dev/") if ns == "dev" else slug
    if not clean_slug or "/" in clean_slug:
        raise SkillLoadError(f"Invalid skill slug: {slug!r}")

    path = (
        skills_root / "dev" / clean_slug / "SKILL.md"
        if ns == "dev"
        else skills_root / clean_slug / "SKILL.md"
    )
    if not path.exists():
        raise SkillLoadError(f"Skill not found: {slug!r} (expected {path})")

    text = path.read_text(encoding="utf-8")
    manifest, body = _parse_frontmatter(text, source_path=path)

    return SkillPackage(
        slug=clean_slug,
        namespace=ns,
        path=path,
        manifest=manifest,
        body=body,
    )


def filter_tools_by_allowed_names(tools: Iterable[Any], allowed_names: Iterable[str]) -> list[Any]:
    """Filter a tool list to the allowed tool names.

    Tool objects may be LangChain tools (with `.name`) or plain callables.
    """
    allowed = {name for name in allowed_names if name}
    if not allowed:
        return []

    filtered: list[Any] = []
    for tool_obj in tools:
        tool_name = _tool_name(tool_obj)
        if tool_name in allowed:
            filtered.append(tool_obj)

    return filtered


def _tool_name(tool_obj: Any) -> str:
    name = getattr(tool_obj, "name", None)
    if isinstance(name, str) and name:
        return name
    func_name = getattr(tool_obj, "__name__", None)
    if isinstance(func_name, str) and func_name:
        return func_name
    return str(tool_obj)


def _parse_frontmatter(text: str, *, source_path: Path) -> tuple[SkillManifest, str]:
    """Parse YAML frontmatter using a minimal subset of YAML.

    Supported:
    - `key: value` scalars (quoted or unquoted)
    - `key:` followed by a list of `- item` (optionally indented)
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillLoadError(f"Missing YAML frontmatter in {source_path}")

    # Collect frontmatter lines until the next `---`
    fm: list[str] = []
    end_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
        fm.append(lines[idx])

    if end_idx is None:
        raise SkillLoadError(f"Unterminated YAML frontmatter in {source_path}")

    data = _parse_minimal_yaml(fm, source_path=source_path)
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")

    name = _require_str(data, "name", source_path=source_path)
    description = _require_str(data, "description", source_path=source_path)
    version = _optional_str(data, "version")
    compatibility = _optional_str(data, "compatibility")
    allowed_tools = tuple(_optional_str_list(data, "allowed-tools"))

    return (
        SkillManifest(
            name=name,
            description=description,
            version=version,
            compatibility=compatibility,
            allowed_tools=allowed_tools,
        ),
        body,
    )


def _parse_minimal_yaml(lines: list[str], *, source_path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        i += 1

        if not line or line.startswith("#"):
            continue

        if ":" not in line:
            raise SkillLoadError(f"Invalid YAML line in {source_path}: {raw!r}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            raise SkillLoadError(f"Invalid YAML key in {source_path}: {raw!r}")

        # List block: key: \n - item
        if value == "":
            items: list[str] = []
            while i < len(lines):
                next_raw = lines[i]
                next_stripped = next_raw.strip()
                if not next_stripped or next_stripped.startswith("#"):
                    i += 1
                    continue
                if ":" in next_stripped and not next_stripped.startswith("-"):
                    break
                if next_stripped.startswith("-"):
                    item = next_stripped.removeprefix("-").strip()
                    items.append(_strip_quotes(item))
                    i += 1
                    continue
                # Nested dict blocks are not supported in the minimal parser; ignore safely.
                break
            data[key] = items
            continue

        data[key] = _strip_quotes(value)

    return data


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _require_str(data: dict[str, Any], key: str, *, source_path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise SkillLoadError(f"Missing or invalid {key!r} in {source_path}")
    return value


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _optional_str_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return [v for v in value if v]
    if isinstance(value, str) and value:
        return [value]
    return []
