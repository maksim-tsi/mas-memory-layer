import asyncio
import json
import importlib.util
import sys
import tempfile
from pathlib import Path

import pytest


def _load_demo_module(project_root: Path):
    spec = importlib.util.spec_from_file_location("llm_client_demo", str(project_root / "scripts/llm_client_demo.py"))
    module = importlib.util.module_from_spec(spec)
    # Insert the module into sys.modules so monkeypatching works with importlib
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeResp:
    def __init__(self, provider="gemini"):
        self.provider = provider
        self.model = "fake-model"
        self.text = "Fake response text"
        self.usage = {"prompt_tokens": 1, "completion_tokens": 1}
        self.metadata = {"debug": True}


class FakeClient:
    def __init__(self, providers=("gemini",)):
        self._providers = list(providers)

    def available_providers(self):
        return self._providers

    async def generate(self, prompt, provider_order=None, model=None):
        # Respect the first provider in provider_order
        chosen = (provider_order[0] if provider_order else self._providers[0])
        return FakeResp(provider=chosen)


@pytest.mark.asyncio
async def test_ndjson_overwrite_and_append(tmp_path, monkeypatch):
    # Setup a temporary project root that the demo uses
    project_root = tmp_path / "project_root"
    project_root.mkdir()
    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir()
    # Copy the script file over to tmp project root so module loads using the temp project root
    orig_script = Path(__file__).resolve().parents[2] / "scripts" / "llm_client_demo.py"
    target_script = scripts_dir / "llm_client_demo.py"
    target_script.write_text(orig_script.read_text())

    # Load module from the temporary scripts path
    demo_module = _load_demo_module(project_root)

    # Monkeypatch the demo's project_root to our tmp project root
    monkeypatch.setattr(demo_module, "project_root", project_root)

    # Create a fake client and monkeypatch `make_client_from_env` to return it
    fake_client = FakeClient(providers=("gemini",))
    monkeypatch.setattr(demo_module, "make_client_from_env", lambda: fake_client)

    # Build a relative output path from the demo's project_root
    output_rel = Path("outputs") / "out.ndjson"
    output_file = project_root / output_rel

    # Run with overwrite mode
    monkeypatch.setattr(sys, "argv", ["llm_client_demo.py", "--json", f"--output-file={output_rel}", "--output-format=ndjson", "--output-mode=overwrite", "--skip-health-check"])  # type: ignore
    await demo_module.demo()

    assert output_file.exists()
    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["provider"] == "gemini"

    # Run again in append mode to add another line
    monkeypatch.setattr(sys, "argv", ["llm_client_demo.py", "--json", f"--output-file={output_rel}", "--output-format=ndjson", "--output-mode=append", "--skip-health-check"])  # type: ignore
    await demo_module.demo()

    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


@pytest.mark.asyncio
async def test_json_array_overwrite_and_append(tmp_path, monkeypatch):
    # Setup project root and copy script to temp path
    project_root = tmp_path / "project_root"
    project_root.mkdir()
    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir()
    orig_script = Path(__file__).resolve().parents[2] / "scripts" / "llm_client_demo.py"
    target_script = scripts_dir / "llm_client_demo.py"
    target_script.write_text(orig_script.read_text())

    demo_module = _load_demo_module(project_root)
    monkeypatch.setattr(demo_module, "project_root", project_root)

    fake_client = FakeClient(providers=("gemini",))
    monkeypatch.setattr(demo_module, "make_client_from_env", lambda: fake_client)

    output_rel = Path("outputs") / "out.json"
    output_file = project_root / output_rel

    # Overwrite write mode: empty array, then write single element
    monkeypatch.setattr(sys, "argv", ["llm_client_demo.py", "--json", f"--output-file={output_rel}", "--output-format=json-array", "--output-mode=overwrite", "--skip-health-check"])  # type: ignore
    await demo_module.demo()

    assert output_file.exists()
    arr = json.loads(output_file.read_text(encoding="utf-8"))
    assert isinstance(arr, list)
    assert len(arr) == 1
    assert arr[0]["provider"] == "gemini"

    # Append mode: start with an existing array and append new item
    output_file.write_text(json.dumps([{"provider": "existing"}], ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["llm_client_demo.py", "--json", f"--output-file={output_rel}", "--output-format=json-array", "--output-mode=append", "--skip-health-check"])  # type: ignore
    await demo_module.demo()

    arr = json.loads(output_file.read_text(encoding="utf-8"))
    # It should now contain the existing element + the newly appended element
    assert any(item.get("provider") == "existing" for item in arr)
    assert any(item.get("provider") == "gemini" for item in arr)

