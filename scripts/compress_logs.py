#!/usr/bin/env python3
"""Compress timestamped log files in logs/ by prefix.

- Combines *.jsonl files matching <prefix>_YYYYMMDD_HHMMSS.jsonl into <prefix>.jsonl
- Combines *.json files matching <prefix>_YYYYMMDD_HHMMSS.json into <prefix>.json (JSON array)
- Removes the original timestamped files after successful write
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"

JSONL_PATTERN = re.compile(r"^(?P<prefix>.+)_\d{8}_\d{6}\.jsonl$")
JSON_PATTERN = re.compile(r"^(?P<prefix>.+)_\d{8}_\d{6}\.json$")


def iter_grouped_files(pattern: re.Pattern[str]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for path in LOG_DIR.iterdir():
        if not path.is_file():
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        prefix = match.group("prefix")
        groups.setdefault(prefix, []).append(path)
    for prefix, files in groups.items():
        groups[prefix] = sorted(files, key=lambda p: p.name)
    return groups


def write_jsonl(output_path: Path, files: Iterable[Path]) -> None:
    with output_path.open("w", encoding="utf-8") as out_handle:
        for path in files:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    out_handle.write(line.rstrip() + "\n")


def write_json_array(output_path: Path, files: Iterable[Path]) -> None:
    combined: list[object] = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        combined.append(data)
    output_path.write_text(json.dumps(combined, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def remove_files(files: Iterable[Path]) -> None:
    for path in files:
        path.unlink()


def main() -> None:
    if not LOG_DIR.exists():
        raise SystemExit(f"logs directory not found: {LOG_DIR}")

    jsonl_groups = iter_grouped_files(JSONL_PATTERN)
    json_groups = iter_grouped_files(JSON_PATTERN)

    for prefix, files in jsonl_groups.items():
        if len(files) < 2:
            continue
        output_path = LOG_DIR / f"{prefix}.jsonl"
        write_jsonl(output_path, files)
        remove_files(files)

    for prefix, files in json_groups.items():
        if len(files) < 2:
            continue
        output_path = LOG_DIR / f"{prefix}.json"
        write_json_array(output_path, files)
        remove_files(files)


if __name__ == "__main__":
    main()
