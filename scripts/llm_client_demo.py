#!/usr/bin/env python3
"""Demonstrate using the LLMClient with real provider adapters.

This script registers the provider adapters using API keys from `.env` (or
environment) and runs a small health check and generation pipeline to show
how the orchestrator picks providers and falls back if needed.

Usage:
  ./scripts/llm_client_demo.py
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.utils.llm_client import LLMClient, ProviderConfig  # noqa: E402
from src.utils.providers import GeminiProvider, GroqProvider, MistralProvider  # noqa: E402


def make_client_from_env() -> LLMClient:
    load_dotenv(dotenv_path=project_root / ".env")
    client = LLMClient()
    if os.getenv("GOOGLE_API_KEY"):
        client.register_provider(GeminiProvider(api_key=os.getenv("GOOGLE_API_KEY")), ProviderConfig(name="gemini", priority=0))
    if os.getenv("GROQ_API_KEY"):
        client.register_provider(GroqProvider(api_key=os.getenv("GROQ_API_KEY")), ProviderConfig(name="groq", priority=1))
    if os.getenv("MISTRAL_API_KEY"):
        client.register_provider(MistralProvider(api_key=os.getenv("MISTRAL_API_KEY")), ProviderConfig(name="mistral", priority=2))
    return client


async def demo():
    client = make_client_from_env()
    print("Registered providers:", client.available_providers())
    if not client.available_providers():
        print("No providers configured in environment. Set GOOGLE_API_KEY, GROQ_API_KEY, or MISTRAL_API_KEY and retry.")
        return

    # Parse CLI arguments early so we can optionally skip health checks quickly
    parser = argparse.ArgumentParser(description="LLMClient demo - query configured providers")
    parser.add_argument("--providers", type=str, default=None, help="Comma-separated list of providers to query (e.g., 'gemini,groq')")
    parser.add_argument("--prompt", type=str, default="What is 2+2? Answer briefly.", help="Prompt to send to providers")
    parser.add_argument("--json", action="store_true", help="Print JSON output for provider responses and usage")
    parser.add_argument("--output-file", type=str, default=None, help="Write JSON output to a file")
    parser.add_argument("--output-format", type=str, choices=["ndjson", "json-array"], default="ndjson", help="Output format when writing to file (ndjson or json-array)")
    parser.add_argument("--output-mode", type=str, choices=["overwrite", "append"], default="overwrite", help="If writing to a file, whether to overwrite or append to existing file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging for the demo (DEBUG level)")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip provider health checks (faster runs for quick demos)")
    parser.add_argument("--model", type=str, default=None, help="Default model to use for all providers unless overridden")
    parser.add_argument("--model-gemini", type=str, default=None, help="Override model for Gemini provider")
    parser.add_argument("--model-groq", type=str, default=None, help="Override model for Groq provider")
    parser.add_argument("--model-mistral", type=str, default=None, help="Override model for Mistral provider")
    args = parser.parse_args()

    prompt = args.prompt
    json_out = args.json
    verbose = args.verbose
    skip_health = args.skip_health_check
    default_model = args.model
    model_overrides = {
        "gemini": args.model_gemini,
        "groq": args.model_groq,
        "mistral": args.model_mistral,
    }
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    requested = args.providers
    available = client.available_providers()
    if requested:
        requested_list = [p.strip().lower() for p in requested.split(",") if p.strip()]
        providers_to_run = [p for p in requested_list if p in available]
        if not providers_to_run:
            print("No requested providers are registered/available; running all registered providers instead.")
            providers_to_run = available
    else:
        providers_to_run = available

    # Optionally skip the health checks (faster demo runs)
    if not skip_health:
        print("Running health checks...")
        health = await client.health_check()
        for name, report in health.items():
            print(f" - {name}: healthy={report.healthy}, details={report.details}, last_error={report.last_error}")
    else:
        print("Skipping health checks (--skip-health-check).")

    # Iterate through each selected provider and request a response from each explicitly
    print(f"Trying generation from each provider: {providers_to_run} (prompt: '{prompt}')")

    # prepare output file for JSON if requested
    output_file_path = None
    output_format = args.output_format
    output_mode = args.output_mode
    collected_outputs = [] if json_out and output_format == "json-array" else None
    if args.output_file and json_out:
        from pathlib import Path
        output_file_path = Path(project_root) / Path(args.output_file)
        # Ensure parent dirs exist
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        if output_format == "ndjson":
            if output_mode == "overwrite":
                output_file_path.write_text("")
            # append mode: leave file as-is
        elif output_format == "json-array":
            # For json-array mode, if overwrite create empty array, if append preserve existing
            if output_mode == "overwrite":
                output_file_path.write_text("[]")

    for provider_name in providers_to_run:
        # Allow per-provider model override, fallback to default `--model` arg
        model_to_use = model_overrides.get(provider_name) or default_model
        try:
            resp = await client.generate(prompt, provider_order=[provider_name], model=model_to_use)
            print(f"\nProvider: {provider_name}")
            if json_out:
                output = {
                    "provider": provider_name,
                    "returned_provider": resp.provider,
                    "model": resp.model,
                    "text": resp.text,
                    "usage": resp.usage,
                    "metadata": resp.metadata,
                }
                # Print to stdout for immediate visibility
                print(json.dumps(output, ensure_ascii=False, indent=2))
                # Handle file output according to format and mode
                if output_file_path:
                    if output_format == "ndjson":
                        with output_file_path.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(output, ensure_ascii=False) + "\n")
                    elif output_format == "json-array":
                        # collect in-memory, write in bulk at the end
                        collected_outputs.append(output)
            else:
                print(f"  Text: {resp.text}")
                print(f"  Model: {resp.model}")
                print(f"  Provider (returned): {resp.provider}")
                if resp.usage:
                    print(f"  Usage: {resp.usage}")
        except Exception as e:
            print(f"\nProvider: {provider_name} (FAILED)")
            print(f"  Error: {e}")

    # Finalize json-array output if needed
    if output_file_path and json_out and output_format == "json-array":
        try:
            import json as _json
            # Read existing array if append mode
            if output_mode == "append" and output_file_path.exists():
                try:
                    existing = _json.loads(output_file_path.read_text(encoding="utf-8") or "[]")
                    merged = existing + (collected_outputs or [])
                except Exception:
                    # If parsing fails, just overwrite
                    merged = collected_outputs or []
            else:
                merged = collected_outputs or []
            output_file_path.write_text(_json.dumps(merged, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            logging.warning("Failed to write JSON array output to file: %s", exc)


if __name__ == "__main__":
    asyncio.run(demo())
