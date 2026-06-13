#!/usr/bin/env python3
"""Quick verification script for Typesense document uploads.

Checks that documents were successfully uploaded to the repository_docs collection.
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment from .env
load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration with fallback chain
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST") or os.getenv("DATA_NODE_IP") or "127.0.0.1"
TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", "8108")
TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "")
COLLECTION_NAME = os.getenv("TYPESENSE_COLLECTION", "mas_project_archive")


def main() -> int:
    """Verify Typesense documents."""
    base_url = f"{TYPESENSE_PROTOCOL}://{TYPESENSE_HOST}:{TYPESENSE_PORT}"
    headers = {"X-TYPESENSE-API-KEY": TYPESENSE_API_KEY}

    print(f"Connecting to Typesense at {base_url}")
    print(f"Collection: {COLLECTION_NAME}")
    print("-" * 60)

    with httpx.Client(base_url=base_url, headers=headers, timeout=30.0) as client:
        # 1. Check collection exists
        try:
            resp = client.get(f"/collections/{COLLECTION_NAME}")
            resp.raise_for_status()
            collection_info = resp.json()
            print("✓ Collection exists")
            print(f"  - Number of documents: {collection_info.get('num_documents', 'unknown')}")
            print(f"  - Fields: {[f['name'] for f in collection_info.get('fields', [])]}")
        except httpx.HTTPStatusError as e:
            print(f"✗ Collection check failed: {e.response.status_code}")
            return 1
        except httpx.RequestError as e:
            print(f"✗ Connection failed: {e}")
            return 1

        print("-" * 60)

        # 2. Search for documents
        search_params = {
            "q": "*",
            "query_by": "content",
            "per_page": 5,
        }
        try:
            resp = client.get(
                f"/collections/{COLLECTION_NAME}/documents/search", params=search_params
            )
            resp.raise_for_status()
            results = resp.json()
            found = results.get("found", 0)
            print(f"✓ Search working - {found} total documents")

            hits = results.get("hits", [])
            if hits:
                print(f"\nSample documents (first {len(hits)}):")
                for i, hit in enumerate(hits, 1):
                    doc = hit.get("document", {})
                    print(f"  {i}. {doc.get('path', 'unknown')}")
                    print(f"     - doc_type: {doc.get('doc_type', 'unknown')}")
                    print(f"     - repo: {doc.get('repository_label', 'unknown')}")
                    content_preview = doc.get("content", "")[:100].replace("\n", " ")
                    print(f"     - content: {content_preview}...")
        except httpx.HTTPStatusError as e:
            print(f"✗ Search failed: {e.response.status_code}")
            return 1

        print("-" * 60)

        # 3. Check for specific document types
        doc_types = ["adr", "spec", "readme", "documentation", "report", "plan"]
        print("\nDocument type distribution:")
        for doc_type in doc_types:
            filter_params = {
                "q": "*",
                "query_by": "content",
                "filter_by": f"doc_type:={doc_type}",
                "per_page": 0,
            }
            try:
                resp = client.get(
                    f"/collections/{COLLECTION_NAME}/documents/search", params=filter_params
                )
                resp.raise_for_status()
                count = resp.json().get("found", 0)
                print(f"  - {doc_type}: {count} documents")
            except httpx.HTTPStatusError:
                print(f"  - {doc_type}: (query failed)")

        print("-" * 60)

        # 4. Test repository_label filter
        filter_params = {
            "q": "*",
            "query_by": "content",
            "filter_by": "repository_label:=mas-memory-layer-repo",
            "per_page": 0,
        }
        try:
            resp = client.get(
                f"/collections/{COLLECTION_NAME}/documents/search", params=filter_params
            )
            resp.raise_for_status()
            count = resp.json().get("found", 0)
            print(f"✓ Documents with repository_label 'mas-memory-layer-repo': {count}")
        except httpx.HTTPStatusError as e:
            print(f"✗ Repository label filter failed: {e.response.status_code}")

        print("-" * 60)
        print("Verification complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
