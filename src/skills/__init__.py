"""Skill loading utilities for YAAM runtime agents.

This package provides minimal, dependency-free helpers for:
- listing available skills under repo root `skills/`,
- loading a selected skill's manifest and body,
- filtering toolsets using `allowed-tools` (progressive disclosure).
"""

from __future__ import annotations

from .loader import (
    SkillLoadError,
    SkillManifest,
    SkillPackage,
    filter_tools_by_allowed_names,
    list_skill_slugs,
    load_skill,
)

__all__ = [
    "SkillLoadError",
    "SkillManifest",
    "SkillPackage",
    "filter_tools_by_allowed_names",
    "list_skill_slugs",
    "load_skill",
]

