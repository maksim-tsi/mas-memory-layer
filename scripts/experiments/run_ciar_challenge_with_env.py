#!/usr/bin/env python3
"""Load CIAR live-run environment from `.env` and run the experiment harness.

This helper intentionally never prints secret values. It reports key names and
presence only, then runs `run_ciar_challenge.py` in a child process with the
loaded environment.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HARNESS = PROJECT_ROOT / "scripts" / "experiments" / "run_ciar_challenge.py"

REQUIRED_KEYS = ("OPENROUTER_API_KEY", "REDIS_URL", "POSTGRES_URL")
DEFAULT_SCENARIOS = ("segment_mismatch", "contradiction_update", "small_talk")
DEFAULT_MODEL = "tencent/hy3-preview"
DEFAULT_DATA_NODE_IP = "192.168.107.187"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a dotenv-style file into key/value pairs without logging values."""
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values


def is_sensitive_key(key: str) -> bool:
    """Return whether a key name likely points at credentials or secret-bearing URLs."""
    return key.endswith(("_API_KEY", "_TOKEN", "_PASSWORD", "_SECRET")) or key in {
        "POSTGRES_URL",
        "REDIS_URL",
    }


def load_env_values(env_path: Path, *, override: bool = False) -> dict[str, Any]:
    """Load dotenv values into os.environ and return non-secret load metadata."""
    parsed = parse_env_file(env_path)
    loaded: list[str] = []
    already_present: list[str] = []
    skipped_existing: list[str] = []

    for key, value in parsed.items():
        if key in os.environ and not override:
            already_present.append(key)
            skipped_existing.append(key)
            continue
        os.environ[key] = value
        loaded.append(key)

    available_sensitive = sorted(
        key for key in set(parsed) | set(os.environ) if is_sensitive_key(key) and os.environ.get(key)
    )
    missing_required = [key for key in REQUIRED_KEYS if not os.environ.get(key)]
    return {
        "env_file_exists": env_path.exists(),
        "loaded_keys": sorted(loaded),
        "already_present_keys": sorted(already_present),
        "skipped_existing_keys": sorted(skipped_existing),
        "available_sensitive_key_names": available_sensitive,
        "missing_required_keys": missing_required,
    }


def replace_url_host_port(url: str, host: str, port: int) -> str:
    """Replace host/port in a URL while preserving credentials, path, and query."""
    parsed = urlsplit(url)
    username = parsed.username or ""
    password = parsed.password
    auth = username
    if password is not None:
        auth = f"{auth}:{password}"
    if auth:
        auth = f"{auth}@"
    netloc = f"{auth}{host}:{port}"
    return urlunsplit(SplitResult(parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def force_data_node_service_urls(data_node_ip: str) -> list[str]:
    """Force service URLs to the active data node without exposing credentials."""
    changed: list[str] = []
    os.environ["REDIS_URL"] = f"redis://{data_node_ip}:6379/0"
    changed.append("REDIS_URL")

    postgres_url = os.environ.get("POSTGRES_URL")
    if postgres_url:
        os.environ["POSTGRES_URL"] = replace_url_host_port(postgres_url, data_node_ip, 5432)
        changed.append("POSTGRES_URL")

    os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = f"http://{data_node_ip}:6006/v1/traces"
    changed.append("PHOENIX_COLLECTOR_ENDPOINT")
    return changed


def print_presence(summary: dict[str, Any]) -> None:
    """Print env presence by key name only."""
    print(f"env_file_exists={summary['env_file_exists']}")
    print("required_key_presence:")
    for key in REQUIRED_KEYS:
        print(f"  {key}={key not in summary['missing_required_keys']}")
    print("available_sensitive_key_names:")
    for key in summary["available_sensitive_key_names"]:
        print(f"  {key}")


def build_harness_command(args: argparse.Namespace) -> list[str]:
    data_node_ip = args.data_node_ip or os.environ.get("DATA_NODE_IP", DEFAULT_DATA_NODE_IP)
    run_id = args.run_id or f"ciar-exp-live-env-{utc_stamp()}"
    phoenix_project_name = args.phoenix_project_name or run_id.replace("ciar-exp-", "ciar-challenge-")
    phoenix_endpoint = args.phoenix_endpoint or f"http://{data_node_ip}:6006/v1/traces"

    os.environ.setdefault("MAS_REDIS_TIMEOUT", str(args.redis_timeout))
    os.environ.setdefault("MAS_OPENROUTER_TIMEOUT", str(args.openrouter_timeout))
    os.environ.setdefault("MAS_MAX_OUTPUT_TOKENS", str(args.max_output_tokens))

    command = [
        sys.executable,
        str(HARNESS),
        "--run-id",
        run_id,
        "--output-dir",
        args.output_dir,
        "--model",
        args.model,
        "--phoenix-endpoint",
        phoenix_endpoint,
        "--phoenix-project-name",
        phoenix_project_name,
        "--provider-health-timeout",
        str(args.provider_health_timeout),
    ]
    if args.skip_provider_health:
        command.extend(
            [
                "--skip-provider-health",
                "--provider-health-skip-reason",
                args.provider_health_skip_reason,
            ]
        )
    if args.require_provider_health:
        command.append("--require-provider-health")
    for scenario_id in args.scenario_id or DEFAULT_SCENARIOS:
        command.extend(["--scenario-id", scenario_id])
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load .env into os.environ and run the focused CIAR live experiment."
    )
    parser.add_argument("--env-file", default=str(PROJECT_ROOT / ".env"))
    parser.add_argument("--override-env", action="store_true")
    parser.add_argument("--print-presence", action="store_true")
    parser.add_argument("--presence-only", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir", default="logs/ciar_challenge")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--phoenix-endpoint")
    parser.add_argument("--phoenix-project-name")
    parser.add_argument("--data-node-ip")
    parser.add_argument(
        "--force-data-node-services",
        action="store_true",
        help="Rewrite Redis/PostgreSQL/Phoenix endpoints to DATA_NODE_IP while preserving credentials.",
    )
    parser.add_argument("--scenario-id", action="append", default=[])
    parser.add_argument("--redis-timeout", type=float, default=15.0)
    parser.add_argument("--openrouter-timeout", type=float, default=120.0)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--provider-health-timeout", type=float, default=45.0)
    parser.add_argument("--skip-provider-health", action="store_true")
    parser.add_argument(
        "--provider-health-skip-reason",
        default="focused live run uses promotion path as provider smoke",
    )
    parser.add_argument("--require-provider-health", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.skip_provider_health and args.require_provider_health:
        raise ValueError("--skip-provider-health cannot be combined with --require-provider-health")

    summary = load_env_values(Path(args.env_file), override=bool(args.override_env))
    if args.force_data_node_services:
        data_node_ip = args.data_node_ip or os.environ.get("DATA_NODE_IP", DEFAULT_DATA_NODE_IP)
        changed_keys = force_data_node_service_urls(data_node_ip)
        print("forced_data_node_service_keys=" + ",".join(changed_keys))
        summary["missing_required_keys"] = [key for key in REQUIRED_KEYS if not os.environ.get(key)]
    if args.print_presence or args.presence_only:
        print_presence(summary)
    if summary["missing_required_keys"]:
        print(
            "missing_required_keys="
            + ",".join(summary["missing_required_keys"])
            + " (values not printed)",
            file=sys.stderr,
        )
        return 2
    if args.presence_only:
        return 0

    command = build_harness_command(args)
    printable_command = " ".join(command)
    print(f"running={printable_command}")
    return subprocess.run(command, cwd=PROJECT_ROOT, env=os.environ.copy(), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
