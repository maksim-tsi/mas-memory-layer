#!/usr/bin/env python3
"""Check OpenRouter connectivity for the configured default model.

This script is intentionally small and non-secret: it loads OPENROUTER_API_KEY
from the environment or local .env, but never prints the key value.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_MODEL = "tencent/hy3-preview"


def load_local_env() -> None:
    """Load .env without printing values."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate OpenRouter connectivity and CIAR task fitness."
    )
    parser.add_argument("--model", default=os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL))
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--max-output-tokens", type=int, default=220)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def summarize_usage(usage: dict[str, Any] | None) -> dict[str, Any]:
    if not usage:
        return {}
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "response_tokens": usage.get("response_tokens"),
        "total_tokens": usage.get("total"),
    }


def sanitize_error(exc: Exception) -> str:
    """Remove provider-side identifiers from exception text."""
    text = str(exc)
    text = re.sub(r"'user_id':\s*'[^']+'", "'user_id': '<redacted>'", text)
    text = re.sub(r'"user_id":\s*"[^"]+"', '"user_id": "<redacted>"', text)
    return text


def assess_task_fitness(text: str, parsed: dict[str, Any] | None, elapsed_s: float) -> dict[str, Any]:
    lowered = text.lower()
    keyword_hits = sorted(
        keyword
        for keyword in ["ciar", "promotion", "l1", "l2", "evidence", "experiment"]
        if keyword in lowered
    )
    return {
        "valid_json_response": parsed is not None,
        "non_empty_response": bool(text.strip()),
        "keyword_hits": keyword_hits,
        "latency_s": round(elapsed_s, 3),
        "fit_for_ciar_experiment_smoke": bool(
            text.strip()
            and elapsed_s <= 45.0
            and ("ciar" in keyword_hits or "evidence" in keyword_hits)
        ),
    }


async def run_check(args: argparse.Namespace) -> dict[str, Any]:
    from src.llm.providers.openrouter import OpenRouterProvider

    logging.getLogger("src.llm.providers.openrouter").setLevel(logging.CRITICAL)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return {
            "ok": False,
            "provider": "openrouter",
            "model": args.model,
            "error": "OPENROUTER_API_KEY is not configured",
        }

    provider = OpenRouterProvider(api_key=api_key)

    health_started = time.perf_counter()
    health = await asyncio.wait_for(provider.health_check(), timeout=args.timeout)
    health_elapsed = time.perf_counter() - health_started
    if not health.healthy:
        return {
            "ok": False,
            "provider": "openrouter",
            "model": args.model,
            "health": {
                "healthy": False,
                "latency_s": round(health_elapsed, 3),
                "details": health.details,
                "last_error": health.last_error,
            },
        }

    prompt = (
        "Return exactly one compact JSON object with keys "
        "status, ciar_relevance, strengths, risks, next_action. "
        "Assess whether this model is fit for YAAM CIAR challenge experiment "
        "smoke tests involving L1 to L2 promotion, evidence review, and "
        "contradiction analysis. Keep arrays to at most two short strings."
    )

    generation_started = time.perf_counter()
    try:
        response = await asyncio.wait_for(
            provider.generate(
                prompt=prompt,
                model=args.model,
                temperature=0.0,
                max_output_tokens=args.max_output_tokens,
                system_instruction="You are a concise reliability smoke-test respondent.",
            ),
            timeout=args.timeout,
        )
    except Exception as exc:
        error = sanitize_error(exc)
        recommendation = None
        if "grok 4.1 fast is deprecated" in error.lower() or "grok-4.3" in error.lower():
            recommendation = "Use --model tencent/hy3-preview or update OPENROUTER_MODEL."
        return {
            "ok": False,
            "provider": "openrouter",
            "model": args.model,
            "api_key_loaded": True,
            "health": {
                "healthy": health.healthy,
                "latency_s": round(health_elapsed, 3),
                "details": health.details,
            },
            "generation": {
                "latency_s": round(time.perf_counter() - generation_started, 3),
                "error_type": type(exc).__name__,
                "error": error,
                "recommendation": recommendation,
            },
            "fitness": {
                "fit_for_ciar_experiment_smoke": False,
                "reason": "generation_failed",
            },
        }
    generation_elapsed = time.perf_counter() - generation_started

    parsed: dict[str, Any] | None = None
    try:
        candidate = response.text.strip()
        parsed_value = json.loads(candidate)
        if isinstance(parsed_value, dict):
            parsed = parsed_value
    except json.JSONDecodeError:
        parsed = None

    fitness = assess_task_fitness(response.text, parsed, generation_elapsed)

    return {
        "ok": bool(health.healthy and fitness["fit_for_ciar_experiment_smoke"]),
        "provider": "openrouter",
        "model": args.model,
        "api_key_loaded": True,
        "health": {
            "healthy": health.healthy,
            "latency_s": round(health_elapsed, 3),
            "details": health.details,
        },
        "generation": {
            "latency_s": round(generation_elapsed, 3),
            "usage": summarize_usage(response.usage),
            "finish_reason": response.metadata.get("finish_reason"),
            "response_preview": response.text.strip()[:500],
        },
        "fitness": fitness,
    }


def print_human(result: dict[str, Any]) -> None:
    status = "PASS" if result.get("ok") else "FAIL"
    print(f"OpenRouter model connectivity: {status}")
    print(f"provider={result.get('provider')}")
    print(f"model={result.get('model')}")
    print(f"api_key_loaded={result.get('api_key_loaded', False)}")

    if "error" in result:
        print(f"error={result['error']}")
        return

    health = result.get("health", {})
    print(f"health_healthy={health.get('healthy')}")
    print(f"health_latency_s={health.get('latency_s')}")
    if health.get("last_error"):
        print(f"health_error={health.get('last_error')}")

    generation = result.get("generation", {})
    if generation:
        print(f"generation_latency_s={generation.get('latency_s')}")
        if generation.get("error"):
            print(f"generation_error_type={generation.get('error_type')}")
            print(f"generation_error={generation.get('error')}")
        if generation.get("recommendation"):
            print(f"recommendation={generation.get('recommendation')}")
        print(f"finish_reason={generation.get('finish_reason')}")
        usage = generation.get("usage") or {}
        if usage:
            print(f"total_tokens={usage.get('total_tokens')}")
        print("response_preview:")
        print(generation.get("response_preview", ""))

    fitness = result.get("fitness", {})
    if fitness:
        print(f"valid_json_response={fitness.get('valid_json_response')}")
        print(f"keyword_hits={','.join(fitness.get('keyword_hits', []))}")
        print(
            "fit_for_ciar_experiment_smoke="
            f"{fitness.get('fit_for_ciar_experiment_smoke')}"
        )


async def async_main() -> int:
    load_local_env()
    args = parse_args()
    result = await run_check(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_human(result)
    return 0 if result.get("ok") else 1


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
