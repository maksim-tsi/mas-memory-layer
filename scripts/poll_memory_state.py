"""Poll wrapper memory_state endpoints and write JSONL timelines."""

from __future__ import annotations

import argparse
import json
import signal
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for memory state polling."""
    parser = argparse.ArgumentParser(description="Poll MAS wrapper memory state")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--error-log", type=str, required=True)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--base-url", type=str, default="http://localhost")
    parser.add_argument("--timeout", type=float, default=5.0)
    return parser.parse_args()


def _write_error(log_path: Path, message: str) -> None:
    timestamp = datetime.now(UTC).isoformat()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def _write_entry(output_path: Path, entry: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def _fetch_sessions(client: httpx.Client, base_url: str) -> list[str]:
    response = client.get(f"{base_url}/sessions")
    response.raise_for_status()
    data = response.json()
    sessions = data.get("sessions", [])
    if not isinstance(sessions, list):
        return []
    return [str(session) for session in sessions]


def _fetch_state(client: httpx.Client, base_url: str, session_id: str) -> dict[str, Any]:
    response = client.get(f"{base_url}/memory_state", params={"session_id": session_id})
    response.raise_for_status()
    return response.json()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    error_path = Path(args.error_log)
    base_url = f"{args.base_url}:{args.port}"

    running = True

    def _stop_handler(_signum: int, _frame: Any) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    with httpx.Client(timeout=args.timeout) as client:
        while running:
            timestamp = datetime.now(UTC).isoformat()
            try:
                sessions = _fetch_sessions(client, base_url)
            except Exception as exc:  # pragma: no cover - defensive logging
                _write_error(error_path, f"sessions fetch failed: {exc}")
                time.sleep(args.interval)
                continue

            for session_id in sessions:
                try:
                    state = _fetch_state(client, base_url, session_id)
                    entry = {
                        "timestamp": timestamp,
                        "session_id": state.get("session_id", session_id),
                        "l1_turns": state.get("l1_turns", 0),
                        "l2_facts": state.get("l2_facts", 0),
                        "l3_episodes": state.get("l3_episodes", 0),
                        "l4_docs": state.get("l4_docs", 0),
                    }
                    _write_entry(output_path, entry)
                except Exception as exc:  # pragma: no cover - defensive logging
                    _write_error(error_path, f"memory_state failed for {session_id}: {exc}")

            time.sleep(args.interval)


if __name__ == "__main__":
    main()
