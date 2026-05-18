#!/usr/bin/env python3
import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _benchmark_dir() -> Path:
    configured = os.environ.get("GOODAI_BENCHMARK_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (PROJECT_ROOT.parent / "goodai-ltm-benchmark-yaam").resolve()


# Adjusting path to include the external benchmark directory
BENCHMARK_DIR = _benchmark_dir()
if not BENCHMARK_DIR.exists():
    raise SystemExit(
        "GoodAI benchmark checkout not found. Set GOODAI_BENCHMARK_DIR "
        f"or clone it to {BENCHMARK_DIR}"
    )
if str(BENCHMARK_DIR) not in sys.path:
    sys.path.append(str(BENCHMARK_DIR))

from dataset_interfaces.factory import DatasetFactory  # noqa: E402

# from runner.run_benchmark import generate_test_examples # We might duplicate logic or use it


def parse_args():
    parser = argparse.ArgumentParser(description="GoodAI LTM Benchmark v2 Orchestrator")
    parser.add_argument("--agent-config", required=True, help="Path to primary agent config (YAML)")
    parser.add_argument("--compare-with", help="Path to challenger agent config (YAML)")
    parser.add_argument(
        "--dataset-config", required=True, help="Path to dataset generation config (YAML)"
    )
    parser.add_argument("--agent-override", action="append", help="Override agent config key=value")
    # parser.add_argument("--bench-override", action="append", help="Override benchmark config key=value") # Dataset config covers this?
    parser.add_argument(
        "--output-dir", default="benchmark_results", help="Directory to save results"
    )
    return parser.parse_args()


def generate_temp_dataset(dataset_config_path: str, output_dir: Path):
    print(f"Generating dataset from {dataset_config_path}...")
    with open(dataset_config_path) as f:
        config = yaml.safe_load(f)

    # We need to mimic what generate_test_examples does but save to output_dir
    # config structure usually has 'datasets' key

    # We construct a fake 'universal_args' if needed or extract from config
    # The dataset_interfaces.factory.create_examples takes (dataset_config, universal_args, max_message_size)

    # In run_benchmark.py:
    # dataset_yaml = loaded_yaml["datasets"]
    # examples.extend(DatasetFactory.create_examples(ds, dataset_yaml["args"], max_message_size))

    # So our dataset_config should probably be the whole yaml or just the datasets part
    # Let's assume input is the full benchmark yaml or specialized dataset yaml

    dataset_yaml = config.get("datasets", config)  # fallback if passed direct list

    # We need max_message_size. For generation it often doesn't matter much (except for chunking)
    # Let's pick a large default or read from agent config?
    # It affects how the dataset is chunked.
    # Ideally should be same as agent's max prompt size.
    # We'll use a safe default 16000 if not specified
    max_message_size = 16000

    examples = []
    # If config has "datasets" list
    if "datasets" in dataset_yaml and isinstance(dataset_yaml["datasets"], list):
        universal_args = dataset_yaml.get("args", {})
        for ds in dataset_yaml["datasets"]:
            examples.extend(DatasetFactory.create_examples(ds, universal_args, max_message_size))
    else:
        # Fallback or error?
        print(
            "Warning: Dataset config format not recognized standard structure. Trying to parse as single dataset list."
        )
        # If it's a list directly...
        pass

    # Save examples
    output_dir.mkdir(parents=True, exist_ok=True)
    for example in examples:
        # We save directly to output_dir/dataset_name/example_id.def.json
        # But TestExample.save uses makes_testdef_path which uses DATA_DIR/run_name...
        # We want to override this.
        # TestExample.save calls self.get_path(run_name)
        # We can just manually save

        # example.dataset_name and example.example_id
        ds_dir = output_dir / example.dataset_name
        ds_dir.mkdir(exist_ok=True)
        file_path = ds_dir / f"{example.example_id}.def.json"

        with open(file_path, "w") as fd:
            json.dump(example.to_dict(), fd, indent=2)

    print(f"Generated {len(examples)} examples in {output_dir}")
    return output_dir


def apply_overrides(config_path: str, overrides: list[str]) -> str:
    # Create temp copy and apply overrides
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if overrides:
        for override in overrides:
            if "=" in override:
                key, value = override.split("=", 1)
                # Handle nested keys dot notation?
                # For now simple top level or specific known keys
                # agent config usually has 'config' -> ...

                # Try to interpret value (int, bool, etc)
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        with contextlib.suppress(ValueError):
                            value = float(value)

                # Simple implementation: locate key in 'config' dict if present
                if "config" in config and key in config["config"]:
                    config["config"][key] = value
                else:
                    # Just add/update root level or 'args'
                    # Depends on what we are overriding.
                    # The requirement says "agent params".
                    pass

    # Save to temp file
    fd, path = tempfile.mkstemp(suffix=".yaml", text=True)
    with os.fdopen(fd, "w") as f:
        yaml.safe_dump(config, f)
    return path


def run_subprocess(agent_config: str, dataset_path: Path, output_dir: str):
    # Construct command
    # python -m runner.run_benchmark -c config ...

    cmd = [
        sys.executable,
        "-m",
        "runner.run_benchmark",
        "-c",
        agent_config,
        "--dataset-path",
        str(dataset_path),
        "--isolated",  # Force isolated mode? Requirement says "Execution Isolation"
    ]

    print(f"Running subprocess: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BENCHMARK_DIR)
    return result.returncode


def main():
    args = parse_args()

    # 1. Generate Dataset
    temp_dataset_dir = Path(tempfile.mkdtemp(prefix="ltm_dataset_"))
    try:
        generate_temp_dataset(args.dataset_config, temp_dataset_dir)

        # 2. Run Agent A
        overrides = args.agent_override or []
        config_a = apply_overrides(args.agent_config, overrides)

        _ret_a = run_subprocess(config_a, temp_dataset_dir, args.output_dir)

        # 3. Run Agent B if requested
        if args.compare_with:
            config_b = apply_overrides(args.compare_with, overrides)  # Are overrides shared? Maybe
            _ret_b = run_subprocess(config_b, temp_dataset_dir, args.output_dir)

    finally:
        # Cleanup dataset? Or keep it for debugging?
        # shutil.rmtree(temp_dataset_dir)
        print(f"Dataset generated at {temp_dataset_dir}")
        pass


if __name__ == "__main__":
    main()
