"""
Structural enforcement: dependency direction for mechanism layer.

Mechanism code under `src/storage/` must not import policy-layer modules.
This test is intentionally simple and fast to keep drift resistance high.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _iter_storage_python_files(repo_root: Path) -> list[Path]:
    storage_root = repo_root / "src" / "storage"
    return sorted(p for p in storage_root.rglob("*.py") if p.is_file())


def _imports_from_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    return modules


def test_storage_does_not_import_policy_layers() -> None:
    """
    Enforce that `src/storage/` does not import from policy layers.

    Policy layers (for this test) include:
    - `src/agents/` (agent orchestration and tool wrappers)
    - `src/evaluation/` (benchmark/eval harness logic)
    - `skills/` (policy-first skill packages)
    """

    repo_root = Path(__file__).resolve().parents[1]
    banned_prefixes = (
        "src.agents",
        "src.evaluation",
        "skills",
        "src.skills",
    )

    violations: list[str] = []
    for py_file in _iter_storage_python_files(repo_root):
        imported = _imports_from_file(py_file)
        banned = sorted(
            mod
            for mod in imported
            if mod == "skills"
            or any(mod.startswith(prefix + ".") or mod == prefix for prefix in banned_prefixes)
        )
        if banned:
            rel = py_file.relative_to(repo_root)
            violations.append(f"{rel}: {', '.join(banned)}")

    assert not violations, "Disallowed imports from policy layers:\n" + "\n".join(violations)
