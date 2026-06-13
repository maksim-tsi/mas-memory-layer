"""Unit tests for the archive_docs_to_typesense script.

Tests cover:
- Path exclusion logic (should_process)
- Document type categorization (determine_doc_type)
- Document scanning (scan_documents)
- CLI argument parsing (parse_args)
- Main workflow with mocked httpx client
"""

import sys
from pathlib import Path

# Add scripts directory to path for import - must be before script imports
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
from archive_docs_to_typesense import (  # noqa: E402
    EXCLUDE_DIRS,
    REPO_LABEL,
    TypesenseClient,
    create_client,
    determine_doc_type,
    init_collection,
    main,
    parse_args,
    scan_documents,
    should_process,
    upload_documents,
)


class TestShouldProcess:
    """Tests for path exclusion logic."""

    def test_excludes_benchmark_directory(self):
        """Benchmark directory should be excluded."""
        assert should_process("benchmarks/goodai-ltm-benchmark/README.md") is False
        assert should_process("./benchmarks/goodai-ltm-benchmark/") is False

    def test_excludes_git_directory(self):
        """Git directory should be excluded."""
        assert should_process(".git/config") is False
        assert should_process("some/path/.git/objects") is False

    def test_excludes_pycache(self):
        """Python cache directories should be excluded."""
        assert should_process("src/__pycache__/module.pyc") is False

    def test_excludes_venv(self):
        """Virtual environment should be excluded."""
        assert should_process(".venv/lib/python3.12") is False

    def test_excludes_htmlcov(self):
        """Coverage reports should be excluded."""
        assert should_process("htmlcov/index.html") is False

    def test_excludes_logs(self):
        """Log directory should be excluded."""
        assert should_process("logs/app.log") is False

    def test_excludes_node_modules(self):
        """Node modules should be excluded."""
        assert should_process("node_modules/package/index.js") is False

    def test_allows_docs_directory(self):
        """Docs directory should be included."""
        assert should_process("docs/README.md") is True
        assert should_process("docs/ADR/001-architecture.md") is True

    def test_allows_src_directory(self):
        """Source directory should be included."""
        assert should_process("src/memory/models.py") is True

    def test_allows_root_files(self):
        """Root level files should be included."""
        assert should_process("README.md") is True
        assert should_process("./DEVLOG.md") is True

    def test_handles_windows_paths(self):
        """Windows-style paths should be normalized and checked."""
        assert should_process("benchmarks\\goodai-ltm-benchmark\\file.md") is False
        assert should_process("docs\\ADR\\001.md") is True


class TestDetermineDocType:
    """Tests for document type categorization."""

    def test_adr_documents(self):
        """ADR documents should be tagged correctly."""
        assert determine_doc_type("docs/ADR/001-architecture.md") == "adr"
        assert determine_doc_type("docs/adr/002-design.md") == "adr"

    def test_specification_documents(self):
        """Spec documents should be tagged as specification."""
        assert determine_doc_type("docs/specs/api-spec.md") == "specification"
        assert determine_doc_type("docs/SPEC-001.md") == "specification"

    def test_plan_documents(self):
        """Plan documents should be tagged correctly."""
        assert determine_doc_type("docs/plan/phase-1.md") == "plan"
        assert determine_doc_type("PLAN.md") == "plan"

    def test_report_documents(self):
        """Report documents should be tagged correctly."""
        assert determine_doc_type("docs/reports/analysis.md") == "report"
        assert determine_doc_type("REPORT-2026.md") == "report"

    def test_readme_documents(self):
        """README files should be tagged correctly."""
        assert determine_doc_type("README.md") == "readme"
        assert determine_doc_type("src/README.md") == "readme"
        assert determine_doc_type("docs/readme.md") == "readme"

    def test_generic_documentation(self):
        """Other documents should be tagged as documentation."""
        assert determine_doc_type("docs/guide.md") == "documentation"
        assert determine_doc_type("DEVLOG.md") == "documentation"
        assert determine_doc_type("src/memory/tiers/CHANGELOG.md") == "documentation"

    def test_case_insensitive(self):
        """Document type detection should be case insensitive."""
        assert determine_doc_type("docs/ADR/file.md") == "adr"
        assert determine_doc_type("docs/Adr/file.md") == "adr"
        assert determine_doc_type("SPEC-file.md") == "specification"


class TestScanDocuments:
    """Tests for document scanning functionality."""

    def test_scans_markdown_files(self, tmp_path):
        """Should find and parse markdown files."""
        # Create test structure
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text("# Test Document\n\nContent here.")
        (tmp_path / "README.md").write_text("# README\n\nProject description.")

        documents = scan_documents(str(tmp_path))

        assert len(documents) == 2
        filenames = [doc["filename"] for doc in documents]
        assert "test.md" in filenames
        assert "README.md" in filenames

    def test_skips_empty_files(self, tmp_path):
        """Should skip empty markdown files."""
        (tmp_path / "empty.md").write_text("")
        (tmp_path / "whitespace.md").write_text("   \n\n   ")
        (tmp_path / "valid.md").write_text("# Content")

        documents = scan_documents(str(tmp_path))

        assert len(documents) == 1
        assert documents[0]["filename"] == "valid.md"

    def test_skips_excluded_directories(self, tmp_path):
        """Should skip excluded directories."""
        # Create excluded directory
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "should_skip.md").write_text("# Should be skipped")

        # Create included directory
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "included.md").write_text("# Included")

        documents = scan_documents(str(tmp_path))

        assert len(documents) == 1
        assert documents[0]["filename"] == "included.md"

    def test_adds_repository_label(self, tmp_path):
        """All documents should have repository label."""
        (tmp_path / "test.md").write_text("# Test")

        documents = scan_documents(str(tmp_path))

        assert len(documents) == 1
        assert documents[0]["repository_label"] == REPO_LABEL

    def test_generates_unique_ids(self, tmp_path):
        """Document IDs should be unique based on path."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "file.md").write_text("# Doc file")
        (tmp_path / "file.md").write_text("# Root file")

        documents = scan_documents(str(tmp_path))

        ids = [doc["id"] for doc in documents]
        assert len(ids) == len(set(ids))  # All unique

    def test_categorizes_doc_types(self, tmp_path):
        """Documents should be categorized by path."""
        adr_dir = tmp_path / "docs" / "ADR"
        adr_dir.mkdir(parents=True)
        (adr_dir / "001.md").write_text("# ADR")

        reports_dir = tmp_path / "docs" / "reports"
        reports_dir.mkdir(parents=True)
        (reports_dir / "analysis.md").write_text("# Report")

        documents = scan_documents(str(tmp_path))

        doc_types = {doc["filename"]: doc["doc_type"] for doc in documents}
        assert doc_types["001.md"] == "adr"
        assert doc_types["analysis.md"] == "report"


class TestParseArgs:
    """Tests for CLI argument parsing."""

    def test_default_values(self):
        """Should have sensible defaults."""
        args = parse_args([])

        assert args.dry_run is False
        assert args.verbose is False
        assert args.collection == "mas_project_archive"

    def test_dry_run_flag(self):
        """--dry-run should be parsed correctly."""
        args = parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_verbose_flag(self):
        """--verbose should be parsed correctly."""
        args = parse_args(["--verbose"])
        assert args.verbose is True

        args = parse_args(["-v"])
        assert args.verbose is True

    def test_collection_override(self):
        """--collection should override default."""
        args = parse_args(["--collection", "custom_collection"])
        assert args.collection == "custom_collection"

    def test_root_dir_override(self):
        """--root-dir should be parsed correctly."""
        args = parse_args(["--root-dir", "/custom/path"])
        assert args.root_dir == "/custom/path"


class TestTypesenseClient:
    """Tests for TypesenseClient dataclass."""

    def test_client_initialization(self):
        """Should initialize with correct attributes."""
        client = TypesenseClient(
            base_url="http://localhost:8108",
            api_key="test_key",
        )
        assert client.base_url == "http://localhost:8108"
        assert client.api_key == "test_key"
        assert client.timeout == 30.0

    def test_headers(self):
        """Should generate correct headers."""
        client = TypesenseClient(
            base_url="http://localhost:8108",
            api_key="my_api_key",
        )
        headers = client._headers()
        assert headers == {"X-TYPESENSE-API-KEY": "my_api_key"}


class TestCreateClient:
    """Tests for Typesense client creation."""

    @patch("archive_docs_to_typesense.TYPESENSE_HOST", "192.168.107.187")
    @patch("archive_docs_to_typesense.TYPESENSE_PORT", "8108")
    @patch("archive_docs_to_typesense.TYPESENSE_PROTOCOL", "http")
    def test_creates_client_with_config(self):
        """Should create client with correct configuration."""
        client = create_client("test_api_key")

        assert isinstance(client, TypesenseClient)
        assert client.api_key == "test_api_key"
        assert client.base_url == "http://192.168.107.187:8108"

    def test_raises_without_api_key(self):
        """Should raise ValueError without API key."""
        with (
            patch("archive_docs_to_typesense.TYPESENSE_API_KEY", None),
            pytest.raises(ValueError, match="API key is required"),
        ):
            create_client(None)


class TestInitCollection:
    """Tests for collection initialization."""

    def test_creates_collection_when_not_exists(self):
        """Should create collection when it doesn't exist."""
        mock_client = MagicMock(spec=TypesenseClient)
        mock_client.get_collection.return_value = None

        init_collection(mock_client, "test_collection")

        mock_client.get_collection.assert_called_once_with("test_collection")
        mock_client.create_collection.assert_called_once()
        schema = mock_client.create_collection.call_args[0][0]
        assert schema["name"] == "test_collection"
        field_names = [f["name"] for f in schema["fields"]]
        assert "filename" in field_names
        assert "content" in field_names
        assert "doc_type" in field_names
        assert "repository_label" in field_names

    def test_skips_creation_when_exists(self):
        """Should skip creation when collection already exists."""
        mock_client = MagicMock(spec=TypesenseClient)
        mock_client.get_collection.return_value = {"name": "test_collection"}

        init_collection(mock_client, "test_collection")

        mock_client.get_collection.assert_called_once_with("test_collection")
        mock_client.create_collection.assert_not_called()


class TestUploadDocuments:
    """Tests for document upload functionality."""

    def test_uploads_documents_successfully(self):
        """Should upload documents and return True on success."""
        mock_client = MagicMock(spec=TypesenseClient)
        mock_client.import_documents.return_value = [
            {"success": True},
            {"success": True},
        ]
        documents = [{"id": "1", "content": "test"}, {"id": "2", "content": "test2"}]

        result = upload_documents(mock_client, "test_collection", documents)

        assert result is True
        mock_client.import_documents.assert_called_once_with(
            "test_collection", documents, action="upsert"
        )

    def test_reports_partial_failures(self):
        """Should report partial upload failures."""
        mock_client = MagicMock(spec=TypesenseClient)
        mock_client.import_documents.return_value = [
            {"success": True},
            {"success": False, "error": "Document too large"},
        ]
        documents = [{"id": "1"}, {"id": "2"}]

        result = upload_documents(mock_client, "test_collection", documents)

        # Partial failure means overall failure
        assert result is False

    def test_handles_upload_exception(self):
        """Should return False on upload exception."""
        mock_client = MagicMock(spec=TypesenseClient)
        mock_client.import_documents.side_effect = Exception("Connection failed")

        result = upload_documents(mock_client, "test_collection", [{"id": "1"}])

        assert result is False


class TestMainWorkflow:
    """Integration tests for main workflow."""

    def test_dry_run_mode(self, tmp_path):
        """Dry run should scan but not upload."""
        # Create test file
        (tmp_path / "test.md").write_text("# Test Document")

        with patch("archive_docs_to_typesense.create_client") as mock_create:
            result = main(["--dry-run", "--root-dir", str(tmp_path)])

        assert result == 0
        mock_create.assert_not_called()

    def test_missing_api_key_without_dry_run(self, tmp_path, monkeypatch):
        """Should fail without API key when not in dry-run mode."""
        monkeypatch.setattr("archive_docs_to_typesense.TYPESENSE_API_KEY", None)

        result = main(["--root-dir", str(tmp_path)])

        assert result == 1

    def test_no_files_found(self, tmp_path):
        """Should handle empty directory gracefully."""
        result = main(["--dry-run", "--root-dir", str(tmp_path)])

        assert result == 0

    @patch("archive_docs_to_typesense.create_client")
    @patch("archive_docs_to_typesense.TYPESENSE_API_KEY", "test_key")
    def test_full_workflow(self, mock_create_client, tmp_path):
        """Should complete full workflow with mocked client."""
        # Create test files
        (tmp_path / "README.md").write_text("# Project")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Guide")

        mock_client = MagicMock(spec=TypesenseClient)
        mock_client.get_collection.return_value = None  # Collection doesn't exist
        mock_client.import_documents.return_value = [
            {"success": True},
            {"success": True},
        ]
        mock_create_client.return_value = mock_client

        result = main(["--root-dir", str(tmp_path)])

        assert result == 0
        mock_create_client.assert_called_once()
        mock_client.create_collection.assert_called_once()
        mock_client.import_documents.assert_called_once()


class TestExcludeDirs:
    """Tests for EXCLUDE_DIRS configuration."""

    def test_benchmark_excluded(self):
        """Benchmark directory should be in exclusion list."""
        assert "benchmarks/goodai-ltm-benchmark" in EXCLUDE_DIRS

    def test_standard_excludes(self):
        """Standard noise directories should be excluded."""
        assert "node_modules" in EXCLUDE_DIRS
        assert ".git" in EXCLUDE_DIRS
        assert "__pycache__" in EXCLUDE_DIRS
        assert ".venv" in EXCLUDE_DIRS
