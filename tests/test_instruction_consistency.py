"""
Instruction consistency checks for agent-first development.

This test prevents instruction drift across:
- AGENTS.MD
- .github/copilot-instructions.md
- .github/instructions/*.md
- GEMINI.MD

The intent is to ensure agents do not pick up unsafe or deprecated patterns
from copy-pastable code snippets inside these files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CodeBlock:
    file: Path
    start_line: int
    language: str
    content: str


def _extract_fenced_code_blocks(markdown: str, file: Path) -> list[CodeBlock]:
    blocks: list[CodeBlock] = []
    in_block = False
    language = ""
    start_line = 0
    buf: list[str] = []

    for idx, line in enumerate(markdown.splitlines(), start=1):
        stripped = line.strip()

        if stripped.startswith("```") and not in_block:
            in_block = True
            language = stripped.removeprefix("```").strip()
            start_line = idx
            buf = []
            continue

        if stripped.startswith("```") and in_block:
            blocks.append(
                CodeBlock(
                    file=file,
                    start_line=start_line,
                    language=language,
                    content="\n".join(buf),
                )
            )
            in_block = False
            language = ""
            start_line = 0
            buf = []
            continue

        if in_block:
            buf.append(line)

    # If a fence is left open, still validate what we saw (better to fail loudly)
    if in_block and buf:
        blocks.append(
            CodeBlock(file=file, start_line=start_line, language=language, content="\n".join(buf))
        )

    return blocks


def test_instruction_files_do_not_contain_banned_snippets() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    instruction_files = [
        repo_root / "AGENTS.MD",
        repo_root / "GEMINI.MD",
        repo_root / ".github" / "copilot-instructions.md",
        *sorted((repo_root / ".github" / "instructions").glob("*.md")),
    ]

    missing = [path for path in instruction_files if not path.exists()]
    assert not missing, f"Expected instruction files to exist: {missing}"

    # Only enforce on code blocks to avoid false positives from prose that forbids the patterns.
    blocks: list[CodeBlock] = []
    for path in instruction_files:
        blocks.extend(_extract_fenced_code_blocks(path.read_text(encoding="utf-8"), file=path))

    banned_patterns: list[tuple[str, re.Pattern[str]]] = [
        ("unittest.mock usage", re.compile(r"\bunittest\.mock\b", re.IGNORECASE)),
        ("pip install", re.compile(r"\bpip\s+install\b", re.IGNORECASE)),
        ("$PIP install", re.compile(r'"\$PIP"\s+install\b', re.IGNORECASE)),
        ("redirect to /tmp", re.compile(r">\s*/tmp/", re.IGNORECASE)),
        ("copilot.out usage", re.compile(r"/tmp/copilot\.out\b", re.IGNORECASE)),
        ("read .env via cat", re.compile(r"\bcat\s+\.env\b", re.IGNORECASE)),
        ("source .env", re.compile(r"\bsource\s+\.env\b", re.IGNORECASE)),
        ("grep .env", re.compile(r"\bgrep\b.*\s\.env\b", re.IGNORECASE)),
        ("export from .env", re.compile(r"\bexport\b.*\s\.env\b", re.IGNORECASE)),
        ("xargs .env", re.compile(r"\bxargs\b.*\s\.env\b", re.IGNORECASE)),
    ]

    violations: list[str] = []
    for block in blocks:
        for label, pattern in banned_patterns:
            if pattern.search(block.content):
                logical_path = block.file.relative_to(repo_root)
                violations.append(
                    f"{logical_path}:{block.start_line}: banned pattern in code block ({label})"
                )

    assert not violations, "Instruction drift detected:\n" + "\n".join(sorted(violations))
