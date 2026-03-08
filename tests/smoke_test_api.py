#!/usr/bin/env python3
"""Smoke test for the API Wall endpoints."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8080"
SESSION_ID = "smoke-test"
TIMEOUT_SECONDS = 5
WAIT_TIMEOUT_SECONDS = 90


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
) -> tuple[int, str]:
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        return exc.code, body
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc


def wait_for_health() -> None:
    deadline = time.time() + WAIT_TIMEOUT_SECONDS
    last_error: str | None = None
    while time.time() < deadline:
        try:
            status, body = _request("GET", f"{BASE_URL}/health")
            if status == 200:
                return
            last_error = f"status={status} body={body}"
        except Exception as exc:  # pragma: no cover - best effort
            last_error = str(exc)
        time.sleep(2)
    raise SystemExit(f"Health check did not become ready: {last_error}")


def main() -> None:
    wait_for_health()

    status, body = _request("GET", f"{BASE_URL}/health")
    assert status == 200, f"Health check failed: {status} {body}"
    print("Health:", body)

    reset_headers = {"X-Session-Id": SESSION_ID}
    status, body = _request(
        "POST",
        f"{BASE_URL}/control/session/reset",
        headers=reset_headers,
    )
    assert status == 200, f"Reset failed: {status} {body}"
    print("Reset:", body)

    chat_headers = {"X-Session-Id": SESSION_ID}
    chat_payload = {
        "messages": [{"role": "user", "content": "Hello, who are you?"}],
        "model": "gemini",
    }
    status, body = _request(
        "POST",
        f"{BASE_URL}/v1/chat/completions",
        headers=chat_headers,
        payload=chat_payload,
    )
    assert status == 200, f"Chat failed: {status} {body}"
    try:
        response_json = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Chat response is not valid JSON: {body}") from exc
    print("Chat:", json.dumps(response_json, indent=2))


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
