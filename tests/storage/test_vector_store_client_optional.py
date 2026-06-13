import builtins

import pytest

from src.storage import vector_store_client


def test_vector_store_client_import_is_independent_from_local_embeddings() -> None:
    assert vector_store_client.QdrantVectorStore is not None


def test_local_embedding_loader_reports_optional_dependency(monkeypatch) -> None:
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("missing optional dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="poetry install --with local-embeddings"):
        vector_store_client._load_sentence_transformer("all-MiniLM-L6-v2")
