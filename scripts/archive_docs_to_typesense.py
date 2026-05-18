"""Archive Markdown documentation to Typesense for semantic search.

This script performs selective ingestion of .md files from the repository,
adding repository labels and doc_type tags based on folder structure.

Uses httpx for direct REST API calls (no typesense SDK dependency),
consistent with src/storage/typesense_adapter.py.

Usage:
    ./.venv/bin/python scripts/archive_docs_to_typesense.py
    ./.venv/bin/python scripts/archive_docs_to_typesense.py --dry-run
    ./.venv/bin/python scripts/archive_docs_to_typesense.py --root-dir /path/to/repo

Environment Variables (from .env):
    TYPESENSE_API_KEY: API key for Typesense authentication (required)
    TYPESENSE_HOST: Typesense host (default: DATA_NODE_IP or 192.168.107.187)
    TYPESENSE_PORT: Typesense port (default: 8108)
    TYPESENSE_PROTOCOL: Protocol (default: http)
    DATA_NODE_IP: Fallback for TYPESENSE_HOST (default: 192.168.107.187)
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables from .env file in project root
# Find .env relative to script location for robustness
_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_FILE)

# --- Configuration ---
# Fallback chain: TYPESENSE_HOST -> DATA_NODE_IP -> 192.168.107.187 (skz-data-lv)
DEFAULT_DATA_NODE_IP = "192.168.107.187"
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", os.getenv("DATA_NODE_IP", DEFAULT_DATA_NODE_IP))
TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", "8108")
TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY")
DEFAULT_COLLECTION_NAME = "mas_project_archive"
REPO_LABEL = "mas-memory-layer-repo"

# Directories to STRICTLY ignore
EXCLUDE_DIRS = {
    "benchmarks/goodai-ltm-benchmark",  # Accidental external benchmark checkout
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "htmlcov",
    "logs",
}


@dataclass
class TypesenseClient:
    """Simple httpx-based Typesense client for REST API calls."""

    base_url: str
    api_key: str
    timeout: float = 30.0

    def _headers(self) -> dict[str, str]:
        """Return headers for Typesense API requests."""
        return {"X-TYPESENSE-API-KEY": self.api_key}

    def get_collection(self, collection_name: str) -> dict | None:
        """Get collection info, returns None if not found."""
        with httpx.Client(headers=self._headers(), timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/collections/{collection_name}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    def create_collection(self, schema: dict) -> dict:
        """Create a new collection."""
        with httpx.Client(headers=self._headers(), timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/collections", json=schema)
            response.raise_for_status()
            return response.json()

    def import_documents(
        self, collection_name: str, documents: list[dict], action: str = "upsert"
    ) -> list[dict]:
        """Import documents using JSONL format.

        Args:
            collection_name: Target collection name.
            documents: List of document dictionaries.
            action: Import action ('create', 'upsert', 'update').

        Returns:
            List of import results (one per document).
        """
        # Typesense import expects JSONL (newline-delimited JSON)
        jsonl_body = "\n".join(json.dumps(doc) for doc in documents)

        with httpx.Client(headers=self._headers(), timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/collections/{collection_name}/documents/import",
                params={"action": action},
                content=jsonl_body,
                headers={**self._headers(), "Content-Type": "text/plain"},
            )
            response.raise_for_status()

            # Parse JSONL response
            results = []
            for line in response.text.strip().split("\n"):
                if line:
                    results.append(json.loads(line))
            return results


def create_client(api_key: str | None = None) -> TypesenseClient:
    """Create and return a Typesense client.

    Args:
        api_key: Optional API key override. Uses TYPESENSE_API_KEY env var if not provided.

    Returns:
        Configured TypesenseClient instance.
    """
    key = api_key or TYPESENSE_API_KEY
    if not key:
        raise ValueError("Typesense API key is required")
    base_url = f"{TYPESENSE_PROTOCOL}://{TYPESENSE_HOST}:{TYPESENSE_PORT}"
    return TypesenseClient(base_url=base_url, api_key=key)


def init_collection(client: TypesenseClient, collection_name: str) -> None:
    """Creates the collection if it doesn't exist.

    Args:
        client: TypesenseClient instance.
        collection_name: Name of the collection to create.
    """
    schema = {
        "name": collection_name,
        "fields": [
            {"name": "filename", "type": "string"},
            {"name": "path", "type": "string"},
            {"name": "content", "type": "string"},
            {"name": "doc_type", "type": "string", "facet": True},
            {"name": "repository_label", "type": "string", "facet": True},
        ],
    }

    existing = client.get_collection(collection_name)
    if existing:
        print(f"[info] Collection {collection_name} already exists. Appending documents.")
    else:
        client.create_collection(schema)
        print(f"✅ Created collection: {collection_name}")


def should_process(root_path: str) -> bool:
    """Returns False if the path is in the exclude list.

    Args:
        root_path: Path to check against exclusion list.

    Returns:
        True if path should be processed, False if it should be skipped.
    """
    # Normalize path separators
    normalized_path = root_path.replace("\\", "/")

    return all(exclusion not in normalized_path for exclusion in EXCLUDE_DIRS)


def determine_doc_type(path: str) -> str:
    """Categorizes the document based on folder structure.

    Args:
        path: File path to categorize.

    Returns:
        Document type string: 'adr', 'specification', 'plan', 'report', 'readme', or 'documentation'.
    """
    lower_path = path.lower()
    if "adr" in lower_path:
        return "adr"
    if "spec" in lower_path:
        return "specification"
    if "plan" in lower_path:
        return "plan"
    if "report" in lower_path:
        return "report"
    if "readme" in lower_path:
        return "readme"
    return "documentation"


def scan_documents(root_dir: str) -> list[dict]:
    """Scan directory for markdown files and prepare document list.

    Args:
        root_dir: Root directory to scan.

    Returns:
        List of document dictionaries ready for Typesense import.
    """
    documents = []

    for root, dirs, files in os.walk(root_dir):
        # Modify dirs in-place to skip excluded directories during walk
        dirs[:] = [d for d in dirs if should_process(os.path.join(root, d))]

        if not should_process(root):
            continue

        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    # Skip empty files
                    if not content.strip():
                        continue

                    # Create relative path for ID generation
                    rel_path = os.path.relpath(file_path, root_dir)
                    doc = {
                        "id": rel_path.replace("/", "_").replace("\\", "_"),
                        "filename": file,
                        "path": rel_path,
                        "content": content,
                        "doc_type": determine_doc_type(file_path),
                        "repository_label": REPO_LABEL,
                    }
                    documents.append(doc)
                    print(f"   Found: {rel_path} ({doc['doc_type']})")

                except Exception as e:
                    print(f"⚠️  Skipping {file_path}: {e}")

    return documents


def upload_documents(client: TypesenseClient, collection_name: str, documents: list[dict]) -> bool:
    """Upload documents to Typesense collection.

    Args:
        client: TypesenseClient instance.
        collection_name: Target collection name.
        documents: List of document dictionaries.

    Returns:
        True if upload succeeded, False otherwise.
    """
    try:
        # action='upsert' ensures we update existing docs if run multiple times
        results = client.import_documents(collection_name, documents, action="upsert")

        # Count successes and failures
        successes = sum(1 for r in results if r.get("success", False))
        failures = len(results) - successes

        if failures > 0:
            print(f"⚠️  Uploaded {successes}/{len(results)} documents ({failures} failures)")
            # Show first few errors
            errors = [r for r in results if not r.get("success", False)][:3]
            for err in errors:
                print(f"   Error: {err.get('error', 'Unknown error')}")
            return failures == 0

        print(f"✅ Success! Uploaded {successes} documents.")
        return True
    except httpx.HTTPStatusError as e:
        print(f"❌ Upload failed: HTTP {e.response.status_code}")
        print(f"   Response: {e.response.text[:500]}")
        return False
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Archive Markdown documentation to Typesense for semantic search.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./.venv/bin/python scripts/archive_docs_to_typesense.py
  ./.venv/bin/python scripts/archive_docs_to_typesense.py --dry-run
  ./.venv/bin/python scripts/archive_docs_to_typesense.py --root-dir /path/to/repo

Environment Variables:
  TYPESENSE_API_KEY    API key for authentication (required)
  TYPESENSE_HOST       Host address (default: DATA_NODE_IP or 192.168.107.187)
  TYPESENSE_PORT       Port number (default: 8108)
  TYPESENSE_PROTOCOL   Protocol (default: http)
""",
    )
    parser.add_argument(
        "--root-dir",
        type=str,
        default=str(_PROJECT_ROOT),
        help="Root directory to scan for markdown files (default: project root)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=DEFAULT_COLLECTION_NAME,
        help=f"Typesense collection name (default: {DEFAULT_COLLECTION_NAME})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and list files without uploading to Typesense",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the archive script.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    args = parse_args(argv)

    if not TYPESENSE_API_KEY and not args.dry_run:
        print("❌ Error: TYPESENSE_API_KEY not found in .env")
        print(f"   Looked in: {_ENV_FILE}")
        return 1

    if args.verbose:
        print("Configuration:")
        print(f"  Host: {TYPESENSE_HOST}:{TYPESENSE_PORT} ({TYPESENSE_PROTOCOL})")
        print(f"  Collection: {args.collection}")
        print(f"  Root dir: {args.root_dir}")
        print(f"  Dry run: {args.dry_run}")

    print(f"🔍 Scanning {args.root_dir} for Markdown files (Skipping benchmark)...")
    documents = scan_documents(args.root_dir)

    if not documents:
        print("⚠️  No markdown files found to archive.")
        return 0

    print(f"\n📄 Found {len(documents)} documents")

    if args.dry_run:
        print("\n🏃 Dry run mode - skipping upload")
        print("\nDocument types breakdown:")
        type_counts: dict[str, int] = {}
        for doc in documents:
            doc_type = doc["doc_type"]
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        for doc_type, count in sorted(type_counts.items()):
            print(f"  {doc_type}: {count}")
        return 0

    # Create client and initialize collection
    client = create_client()
    init_collection(client, args.collection)

    print(f"\n🚀 Uploading {len(documents)} documents to Typesense...")
    success = upload_documents(client, args.collection, documents)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
