#!/usr/bin/env python3
"""Check YAAM data-node service reachability without printing secrets."""

from __future__ import annotations

import argparse
import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_TIMEOUT_S = 5.0


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    env_key: str
    default_port: int
    protocol: str
    health_path: str | None = None


SERVICE_SPECS: dict[str, ServiceSpec] = {
    "redis": ServiceSpec("redis", "REDIS_URL", 6379, "redis"),
    "postgres": ServiceSpec("postgres", "POSTGRES_URL", 5432, "tcp"),
    "phoenix": ServiceSpec(
        "phoenix", "PHOENIX_COLLECTOR_ENDPOINT", 6006, "http", health_path="/"
    ),
    "qdrant": ServiceSpec("qdrant", "QDRANT_URL", 6333, "http", health_path="/healthz"),
    "neo4j": ServiceSpec("neo4j", "NEO4J_URI", 7687, "tcp"),
    "typesense": ServiceSpec("typesense", "TYPESENSE_URL", 8108, "http", health_path="/health"),
}


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse dotenv-style key/value pairs without shell expansion."""
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
        if key:
            values[key] = value.strip().strip('"').strip("'")
    return values


def endpoint_summary(value: str, default_port: int) -> dict[str, Any]:
    """Return non-secret URL metadata for reporting."""
    parsed = urlparse(value)
    if parsed.scheme:
        return {
            "scheme": parsed.scheme,
            "host": parsed.hostname,
            "port": parsed.port or default_port,
            "path_present": bool(parsed.path and parsed.path != "/"),
            "user_present": bool(parsed.username),
            "password_present": bool(parsed.password),
        }
    host, _, port_text = value.partition(":")
    port = int(port_text) if port_text.isdigit() else default_port
    return {
        "scheme": "",
        "host": host or None,
        "port": port,
        "path_present": False,
        "user_present": False,
        "password_present": False,
    }


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def tcp_check(host: str, port: int, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return {"ok": True, "elapsed_ms": _elapsed_ms(started)}
    except OSError as exc:
        return {
            "ok": False,
            "elapsed_ms": _elapsed_ms(started),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def redis_ping(host: str, port: int, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout_s) as sock:
            sock.settimeout(timeout_s)
            sock.sendall(b"*1\r\n$4\r\nPING\r\n")
            response = sock.recv(64)
        return {
            "ok": response.startswith(b"+PONG"),
            "elapsed_ms": _elapsed_ms(started),
            "response": "PONG" if response.startswith(b"+PONG") else "unexpected",
        }
    except OSError as exc:
        return {
            "ok": False,
            "elapsed_ms": _elapsed_ms(started),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def http_check(
    scheme: str,
    host: str,
    port: int,
    path: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    started = time.perf_counter()
    url = f"{scheme or 'http'}://{host}:{port}{path}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "yaam-data-node-check"})
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            response.read(80)
            return {
                "ok": 200 <= int(response.status) < 500,
                "elapsed_ms": _elapsed_ms(started),
                "status": int(response.status),
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "elapsed_ms": _elapsed_ms(started),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def check_service(
    spec: ServiceSpec,
    env_values: dict[str, str],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    value = env_values.get(spec.env_key)
    result: dict[str, Any] = {
        "service": spec.name,
        "env_key": spec.env_key,
        "present": bool(value),
        "endpoint": None,
        "tcp": {"ok": False, "error": "missing endpoint"},
        "protocol": {"ok": False, "skipped": True, "reason": "missing endpoint"},
        "ok": False,
    }
    if not value:
        return result

    endpoint = endpoint_summary(value, spec.default_port)
    result["endpoint"] = endpoint
    host = endpoint.get("host")
    port = endpoint.get("port")
    if not host or not isinstance(port, int):
        result["tcp"] = {"ok": False, "error": "missing host or port"}
        result["protocol"] = {"ok": False, "skipped": True, "reason": "missing host or port"}
        return result

    result["tcp"] = tcp_check(host, port, timeout_s)
    if not result["tcp"]["ok"]:
        result["protocol"] = {"ok": False, "skipped": True, "reason": "tcp failed"}
        return result

    if spec.protocol == "redis":
        result["protocol"] = redis_ping(host, port, timeout_s)
    elif spec.protocol == "http" and spec.health_path:
        result["protocol"] = http_check(
            str(endpoint.get("scheme") or "http"), host, port, spec.health_path, timeout_s
        )
    else:
        result["protocol"] = {"ok": True, "skipped": True, "reason": "tcp-only service"}

    result["ok"] = bool(result["tcp"].get("ok") and result["protocol"].get("ok"))
    return result


def run_checks(
    env_path: Path,
    services: list[str],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    env_values = parse_env_file(env_path)
    selected = services or list(SERVICE_SPECS)
    results = [check_service(SERVICE_SPECS[name], env_values, timeout_s=timeout_s) for name in selected]
    return {
        "env_file_exists": env_path.exists(),
        "services": results,
        "ok": all(result["ok"] for result in results),
    }


def render_text(payload: dict[str, Any]) -> str:
    lines = [f"env_file_exists={payload['env_file_exists']}"]
    for result in payload["services"]:
        endpoint = result.get("endpoint") or {}
        lines.append(
            "{service}: present={present} ok={ok} scheme={scheme} host={host} port={port} "
            "path_present={path_present} user_present={user_present} "
            "password_present={password_present} tcp_ok={tcp_ok} protocol_ok={protocol_ok}".format(
                service=result["service"],
                present=result["present"],
                ok=result["ok"],
                scheme=endpoint.get("scheme"),
                host=endpoint.get("host"),
                port=endpoint.get("port"),
                path_present=endpoint.get("path_present"),
                user_present=endpoint.get("user_present"),
                password_present=endpoint.get("password_present"),
                tcp_ok=(result.get("tcp") or {}).get("ok"),
                protocol_ok=(result.get("protocol") or {}).get("ok"),
            )
        )
    lines.append(f"overall_ok={payload['ok']}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check YAAM data-node service endpoints from a local .env file."
    )
    parser.add_argument("--env-file", default=".env")
    parser.add_argument(
        "--service",
        action="append",
        choices=tuple(SERVICE_SPECS),
        default=[],
        help="Service to check. Repeat to check multiple services. Defaults to all services.",
    )
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = run_checks(Path(args.env_file), list(args.service), timeout_s=float(args.timeout_s))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_text(payload))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
