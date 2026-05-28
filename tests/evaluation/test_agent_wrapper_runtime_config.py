"""Runtime configuration tests for the API Wall wrapper."""

from __future__ import annotations

from argparse import Namespace

from src.evaluation import agent_wrapper


def test_build_config_reads_runtime_yaml_and_sets_provider_env(
    tmp_path, monkeypatch
) -> None:
    """Tracked runtime config should drive L3/L4 and OpenRouter defaults."""
    runtime_config = tmp_path / "runtime.yaml"
    runtime_config.write_text(
        "\n".join(
            [
                "llm:",
                "  openrouter_model: tencent/hy3-preview",
                "  openrouter_embedding_model: qwen/qwen3-embedding-8b",
                "project:",
                "  id: test",
                "memory:",
                "  l3:",
                "    collection_name: yaam-test-episodes",
                "    vector_size: 4096",
                "  l4:",
                "    collection_name: yaam-test",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("YAAM_RUNTIME_CONFIG", str(runtime_config))
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://test:test@localhost:5432/test")
    for key in (
        "OPENROUTER_MODEL",
        "OPENROUTER_EMBEDDING_MODEL",
        "YAAM_PROJECT_ID",
        "MAS_L3_COLLECTION",
        "EMBEDDING_DIMENSIONS",
        "MAS_L4_COLLECTION",
    ):
        monkeypatch.delenv(key, raising=False)

    config = agent_wrapper.build_config(
        Namespace(agent_type="full", agent_variant="unit", port=8080, model="test-model")
    )

    assert config.openrouter_model == "tencent/hy3-preview"
    assert config.openrouter_embedding_model == "qwen/qwen3-embedding-8b"
    assert config.project_id == "test"
    assert config.l3_collection_name == "yaam-test-episodes"
    assert config.l3_vector_size == 4096
    assert config.l4_collection_name == "yaam-test"
    assert agent_wrapper.os.environ["OPENROUTER_MODEL"] == "tencent/hy3-preview"
    assert agent_wrapper.os.environ["OPENROUTER_EMBEDDING_MODEL"] == "qwen/qwen3-embedding-8b"
    assert agent_wrapper.os.environ["YAAM_PROJECT_ID"] == "test"
    assert agent_wrapper.os.environ["MAS_L3_COLLECTION"] == "yaam-test-episodes"
    assert agent_wrapper.os.environ["EMBEDDING_DIMENSIONS"] == "4096"
    assert agent_wrapper.os.environ["MAS_L4_COLLECTION"] == "yaam-test"


def test_runtime_env_overrides_yaml_values(tmp_path, monkeypatch) -> None:
    """Environment values remain authoritative over runtime.yaml defaults."""
    runtime_config = tmp_path / "runtime.yaml"
    runtime_config.write_text(
        "\n".join(
            [
                "llm:",
                "  openrouter_model: old-model",
                "  openrouter_embedding_model: old-embedding",
                "memory:",
                "  l3:",
                "    collection_name: old_l3",
                "    vector_size: 768",
                "  l4:",
                "    collection_name: old_l4",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("YAAM_RUNTIME_CONFIG", str(runtime_config))
    monkeypatch.setenv("OPENROUTER_MODEL", "tencent/hy3-preview")
    monkeypatch.setenv("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
    monkeypatch.setenv("YAAM_PROJECT_ID", "scm-bench")
    monkeypatch.setenv("MAS_L3_COLLECTION", "episodes_qwen_v2")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "4096")
    monkeypatch.setenv("MAS_L4_COLLECTION", "knowledge_base_v2")

    settings = agent_wrapper.load_runtime_settings()

    assert settings.openrouter_model == "tencent/hy3-preview"
    assert settings.openrouter_embedding_model == "qwen/qwen3-embedding-8b"
    assert settings.project_id == "scm-bench"
    assert settings.l3_collection_name == "episodes_qwen_v2"
    assert settings.l3_vector_size == 4096
    assert settings.l4_collection_name == "knowledge_base_v2"


def test_project_id_env_derives_default_collections(tmp_path, monkeypatch) -> None:
    runtime_config = tmp_path / "runtime.yaml"
    runtime_config.write_text("project:\n  id: test\nmemory:\n  l3:\n    vector_size: 4096\n", encoding="utf-8")
    monkeypatch.setenv("YAAM_RUNTIME_CONFIG", str(runtime_config))
    monkeypatch.setenv("YAAM_PROJECT_ID", "cognitive-sandwich")
    monkeypatch.delenv("MAS_L3_COLLECTION", raising=False)
    monkeypatch.delenv("MAS_L4_COLLECTION", raising=False)

    settings = agent_wrapper.load_runtime_settings()

    assert settings.project_id == "cognitive-sandwich"
    assert settings.l3_collection_name == "yaam-cognitive-sandwich-episodes"
    assert settings.l4_collection_name == "yaam-cognitive-sandwich"
