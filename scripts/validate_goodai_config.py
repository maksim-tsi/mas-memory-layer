"""Validate GoodAI benchmark configuration files.

This script performs a lightweight schema validation for GoodAI LTM Benchmark
configuration files to ensure that subset runs are well-formed before execution.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_DATASETS = {
    "prospective_memory",
    "restaurant",
    "colours",
    "shopping",
    "locations_directions",
    "name_list",
    "jokes",
    "sallyanne",
    "trigger_response",
    "spy_meeting",
    "chapterbreak",
}


class ConfigValidationError(Exception):
    """Raised when the configuration does not meet expected structure."""


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ConfigValidationError(f"Config file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"Invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigValidationError("Top-level YAML must be a mapping.")
    return data


def _require_mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ConfigValidationError(f"Missing or invalid mapping for '{key}'.")
    return value


def _require_list(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        raise ConfigValidationError(f"Missing or invalid list for '{key}'.")
    return value


def _require_positive_int(value: Any, field_name: str) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ConfigValidationError(f"'{field_name}' must be a positive integer.")


def validate_config(config_path: Path) -> None:
    data = _load_yaml(config_path)

    config_block = _require_mapping(data, "config")
    run_name = config_block.get("run_name")
    if not isinstance(run_name, str) or not run_name.strip():
        raise ConfigValidationError("config.run_name must be a non-empty string.")

    datasets_block = _require_mapping(data, "datasets")
    args_block = _require_mapping(datasets_block, "args")
    memory_span = args_block.get("memory_span")
    dataset_examples = args_block.get("dataset_examples")

    _require_positive_int(memory_span, "datasets.args.memory_span")
    _require_positive_int(dataset_examples, "datasets.args.dataset_examples")

    datasets_list = _require_list(datasets_block, "datasets")
    if not datasets_list:
        raise ConfigValidationError("datasets.datasets must contain at least one dataset.")

    unknown = []
    for entry in datasets_list:
        if not isinstance(entry, dict):
            raise ConfigValidationError("Each dataset entry must be a mapping.")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigValidationError("Each dataset entry must include a non-empty 'name'.")
        if name not in SUPPORTED_DATASETS:
            unknown.append(name)

    if unknown:
        raise ConfigValidationError(f"Unsupported dataset names: {', '.join(sorted(set(unknown)))}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a GoodAI LTM Benchmark configuration file.",
    )
    parser.add_argument(
        "config_path",
        type=Path,
        help="Path to the GoodAI benchmark YAML configuration file.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        validate_config(args.config_path)
    except ConfigValidationError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    print("Validation succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
