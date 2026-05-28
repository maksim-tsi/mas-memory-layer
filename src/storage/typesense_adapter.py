"""
Typesense full-text search adapter for declarative memory (L5).

This adapter provides fast, typo-tolerant full-text search for
distilled knowledge and facts.

Features:
- Document indexing
- Full-text search with typo tolerance
- Faceted search
- Schema management
"""

import asyncio
import json
import logging
import uuid
from datetime import UTC
from typing import Any, overload

import httpx

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageDataError,
    StorageQueryError,
    validate_required_fields,
)
from .metrics import OperationTimer

logger = logging.getLogger(__name__)


class TypesenseAdapter(StorageAdapter):
    """
    Typesense adapter for full-text search (L5 declarative memory).

    Configuration:
        {
            'url': 'http://host:port',
            'api_key': 'your_api_key',
            'collection_name': 'declarative_memory',
            'schema': {
                'name': 'declarative_memory',
                'fields': [
                    {'name': 'content', 'type': 'string'},
                    {'name': 'session_id', 'type': 'string', 'facet': True},
                    {'name': 'created_at', 'type': 'int64'}
                ]
            }
        }

    Example:
        ```python
        config = {
            'url': 'http://192.168.107.187:8108',
            'api_key': os.getenv('TYPESENSE_API_KEY'),
            'collection_name': 'declarative_memory'
        }

        adapter = TypesenseAdapter(config)
        await adapter.connect()

        # Index document
        await adapter.store({
            'content': 'User prefers dark mode',
            'session_id': 'session-123',
            'fact_type': 'preference'
        })

        # Search
        results = await adapter.search({
            'q': 'dark mode',
            'query_by': 'content',
            'limit': 5
        })
        ```
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.url = config.get("url", "").rstrip("/")
        self.api_key = config.get("api_key")
        self.collection_name = config.get("collection_name", "declarative_memory")
        self.schema = config.get("schema")
        self.reconcile_schema = bool(config.get("reconcile_schema", True))
        self._schema_warnings: list[str] = []
        self.client: httpx.AsyncClient | None = None

        if not self.url or not self.api_key:
            raise StorageDataError("Typesense URL and API key required")

        logger.info(f"TypesenseAdapter initialized (collection: {self.collection_name})")

    async def _raise_for_status(self, response: httpx.Response) -> None:
        """Awaitable-safe wrapper for raise_for_status to support AsyncMock responses."""
        maybe_coro = response.raise_for_status()
        if asyncio.iscoroutine(maybe_coro):
            await maybe_coro

    async def _response_json(self, response: httpx.Response) -> Any:
        """Return JSON from real httpx responses and async test doubles."""
        json_result = response.json()
        if asyncio.iscoroutine(json_result):
            json_result = await json_result
        return json_result

    def _get_default_schema(self) -> dict[str, Any]:
        """
        Get default schema for auto-creating collection.

        Provides a flexible schema for L4 knowledge documents plus legacy facts.
        """
        return {
            "name": self.collection_name,
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "content", "type": "string"},
                {"name": "session_id", "type": "string", "facet": True, "optional": True},
                {"name": "title", "type": "string", "optional": True},
                {"name": "knowledge_type", "type": "string", "facet": True, "optional": True},
                {"name": "confidence_score", "type": "float", "optional": True},
                {"name": "source_episode_ids", "type": "string[]", "optional": True},
                {"name": "episode_count", "type": "int32", "optional": True},
                {"name": "provenance_links", "type": "string[]", "optional": True},
                {"name": "category", "type": "string", "facet": True, "optional": True},
                {"name": "tags", "type": "string[]", "facet": True, "optional": True},
                {"name": "domain", "type": "string", "facet": True, "optional": True},
                {"name": "distilled_at", "type": "int64", "optional": True},
                {"name": "access_count", "type": "int32", "optional": True},
                {"name": "usefulness_score", "type": "float", "optional": True},
                {"name": "validation_count", "type": "int32", "optional": True},
                {"name": "timestamp", "type": "int64", "optional": True},
                {"name": "fact_type", "type": "string", "facet": True, "optional": True},
                {"name": "created_at", "type": "int64", "optional": True},
            ],
        }

    async def _reconcile_collection_schema(self, collection_info: dict[str, Any]) -> None:
        """Add missing fields to an existing collection without destructive changes."""
        if not self.client or not self.reconcile_schema:
            return

        desired_schema = self.schema or self._get_default_schema()
        desired_fields = desired_schema.get("fields", [])
        current_fields = {
            str(field.get("name")): field
            for field in collection_info.get("fields", [])
            if field.get("name")
        }

        missing_fields: list[dict[str, Any]] = []
        incompatible_fields: list[str] = []
        for desired_field in desired_fields:
            field_name = str(desired_field.get("name", ""))
            if not field_name:
                continue
            if field_name == "id":
                continue
            current_field = current_fields.get(field_name)
            if current_field is None:
                missing_fields.append(dict(desired_field))
                continue
            if current_field.get("type") != desired_field.get("type"):
                incompatible_fields.append(
                    f"{field_name}: current={current_field.get('type')} desired={desired_field.get('type')}"
                )

        if incompatible_fields:
            warning = (
                f"Typesense schema drift in {self.collection_name}: "
                f"{'; '.join(incompatible_fields)}"
            )
            self._schema_warnings.append(warning)
            logger.warning(warning)

        if not missing_fields:
            return

        try:
            response = await self.client.patch(
                f"{self.url}/collections/{self.collection_name}",
                json={"fields": missing_fields},
            )
            await self._raise_for_status(response)
            logger.info(
                "Typesense schema reconciled for %s: added fields=%s",
                self.collection_name,
                [field["name"] for field in missing_fields],
            )
        except Exception as e:
            warning = f"Typesense schema reconciliation failed for {self.collection_name}: {e}"
            self._schema_warnings.append(warning)
            logger.warning(warning)

    async def connect(self) -> None:
        """Connect to Typesense and ensure collection exists"""
        async with OperationTimer(self.metrics, "connect"):
            if not self.api_key:
                raise StorageDataError("Typesense API key required")

            try:
                self.client = httpx.AsyncClient(
                    headers={"X-TYPESENSE-API-KEY": str(self.api_key)}, timeout=10.0
                )

                # Check if collection exists
                response = await self.client.get(f"{self.url}/collections/{self.collection_name}")

                if response.status_code == 404:
                    # Create collection with provided schema or default
                    schema_to_use = self.schema or self._get_default_schema()
                    response = await self.client.post(f"{self.url}/collections", json=schema_to_use)
                    await self._raise_for_status(response)
                    logger.info(f"Created collection: {self.collection_name}")
                else:
                    await self._raise_for_status(response)
                    if self.reconcile_schema:
                        collection_info = await self._response_json(response)
                        if isinstance(collection_info, dict):
                            await self._reconcile_collection_schema(collection_info)

                self._connected = True
                logger.info(f"Connected to Typesense at {self.url}")

            except Exception as e:
                logger.error(f"Typesense connection failed: {e}", exc_info=True)
                raise StorageConnectionError(f"Failed to connect: {e}") from e

    async def disconnect(self) -> None:
        """Close Typesense connection"""
        async with OperationTimer(self.metrics, "disconnect"):
            if self.client:
                await self.client.aclose()
                self.client = None
                self._connected = False
                logger.info("Disconnected from Typesense")

    async def store(self, data: dict[str, Any]) -> str:
        """Index document in Typesense"""
        async with OperationTimer(self.metrics, "store"):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")

            try:
                # Add auto-generated ID if not present
                if "id" not in data:
                    data["id"] = str(uuid.uuid4())

                response = await self.client.post(
                    f"{self.url}/collections/{self.collection_name}/documents", json=data
                )
                await self._raise_for_status(response)

                result = await self._response_json(response)

                document_id = str(result["id"])
                logger.debug(f"Indexed document: {document_id}")
                return document_id

            except httpx.HTTPStatusError as e:
                logger.error(f"Typesense store failed: {e}", exc_info=True)
                raise StorageQueryError(f"Store failed: {e}") from e
            except Exception as e:
                logger.error(f"Typesense store failed: {e}", exc_info=True)
                raise StorageQueryError(f"Store failed: {e}") from e

        raise AssertionError("Unreachable")

    async def retrieve(self, id: str) -> dict[str, Any] | None:
        """Retrieve document by ID"""
        async with OperationTimer(self.metrics, "retrieve"):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")

            try:
                response = await self.client.get(
                    f"{self.url}/collections/{self.collection_name}/documents/{id}"
                )

                if response.status_code == 404:
                    return None

                await self._raise_for_status(response)
                result = await self._response_json(response)

                return dict(result)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                logger.error(f"Typesense retrieve failed: {e}", exc_info=True)
                raise StorageQueryError(f"Retrieve failed: {e}") from e
            except Exception as e:
                logger.error(f"Typesense retrieve failed: {e}", exc_info=True)
                raise StorageQueryError(f"Retrieve failed: {e}") from e

        raise AssertionError("Unreachable")

    async def get_document(self, collection_name: str, document_id: str) -> dict[str, Any] | None:
        """Retrieve a document by ID from a specified collection."""
        async with OperationTimer(self.metrics, "get_document"):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")

            try:
                response = await self.client.get(
                    f"{self.url}/collections/{collection_name}/documents/{document_id}"
                )

                if response.status_code == 404:
                    return None

                await self._raise_for_status(response)
                result = await self._response_json(response)

                return dict(result)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                logger.error(f"Typesense get_document failed: {e}", exc_info=True)
                raise StorageQueryError(f"Get document failed: {e}") from e
            except Exception as e:
                logger.error(f"Typesense get_document failed: {e}", exc_info=True)
                raise StorageQueryError(f"Get document failed: {e}") from e

        raise AssertionError("Unreachable")

    async def update_document(
        self,
        collection_name: str,
        document_id: str,
        document: dict[str, Any],
    ) -> bool:
        """Update a document in a specified collection."""
        async with OperationTimer(self.metrics, "update_document"):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")

            try:
                response = await self.client.patch(
                    f"{self.url}/collections/{collection_name}/documents/{document_id}",
                    json=document,
                )
                await self._raise_for_status(response)
                return bool(response.status_code == 200)

            except httpx.HTTPStatusError as e:
                logger.error(f"Typesense update_document failed: {e}", exc_info=True)
                raise StorageQueryError(f"Update document failed: {e}") from e
            except Exception as e:
                logger.error(f"Typesense update_document failed: {e}", exc_info=True)
                raise StorageQueryError(f"Update document failed: {e}") from e

        raise AssertionError("Unreachable")

    async def delete_document(self, collection_name: str, document_id: str) -> bool:
        """Delete a document by ID from a specified collection."""
        async with OperationTimer(self.metrics, "delete_document"):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")

            try:
                response = await self.client.delete(
                    f"{self.url}/collections/{collection_name}/documents/{document_id}"
                )
                return bool(response.status_code == 200)

            except Exception as e:
                logger.error(f"Typesense delete_document failed: {e}", exc_info=True)
                return False

        raise AssertionError("Unreachable")

    @overload
    async def search(self, query: dict[str, Any]) -> list[dict[str, Any]]: ...

    @overload
    async def search(
        self,
        *,
        collection_name: str,
        query: str,
        query_by: str,
        filter_by: str | None = None,
        limit: int = 10,
        sort_by: str | None = None,
    ) -> dict[str, Any]: ...

    async def search(
        self,
        query: dict[str, Any] | str | None = None,
        *,
        collection_name: str | None = None,
        query_by: str | None = None,
        filter_by: str | None = None,
        limit: int = 10,
        sort_by: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Full-text search.

        Query params:
            - q: Search query
            - query_by: Fields to search
            - filter_by: Optional filters
            - limit: Max results (default: 10)
        """
        async with OperationTimer(self.metrics, "search"):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")

            if isinstance(query, dict):
                validate_required_fields(query, ["q", "query_by"])
                params = {
                    "q": query["q"],
                    "query_by": query["query_by"],
                    "per_page": query.get("limit", 10),
                }
                if "filter_by" in query:
                    params["filter_by"] = query["filter_by"]
                if "sort_by" in query:
                    params["sort_by"] = query["sort_by"]
                if "facet_by" in query:
                    params["facet_by"] = query["facet_by"]
                target_collection = query.get("collection_name", self.collection_name)
            else:
                if query is None or not query_by:
                    raise StorageDataError("Search requires query and query_by")
                params = {
                    "q": query,
                    "query_by": query_by,
                    "per_page": limit,
                }
                if filter_by:
                    params["filter_by"] = filter_by
                if sort_by:
                    params["sort_by"] = sort_by
                target_collection = collection_name or self.collection_name

            try:
                response = await self.client.get(
                    f"{self.url}/collections/{target_collection}/documents/search", params=params
                )
                await self._raise_for_status(response)

                result = await self._response_json(response)

                if isinstance(query, dict):
                    return [hit["document"] for hit in result.get("hits", [])]

                return dict(result)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 422 and "sort_by" in params:
                    retry_params = dict(params)
                    invalid_sort = retry_params.pop("sort_by")
                    logger.warning(
                        "Typesense search rejected sort_by=%s for collection=%s; "
                        "retrying without sort_by",
                        invalid_sort,
                        target_collection,
                    )
                    try:
                        response = await self.client.get(
                            f"{self.url}/collections/{target_collection}/documents/search",
                            params=retry_params,
                        )
                        await self._raise_for_status(response)
                        result = await self._response_json(response)
                        if isinstance(query, dict):
                            return [hit["document"] for hit in result.get("hits", [])]
                        return dict(result)
                    except Exception as retry_error:
                        logger.error(
                            f"Typesense search retry without sort_by failed: {retry_error}",
                            exc_info=True,
                        )
                        raise StorageQueryError(f"Search failed: {retry_error}") from retry_error
                logger.error(f"Typesense search failed: {e}", exc_info=True)
                raise StorageQueryError(f"Search failed: {e}") from e
            except Exception as e:
                logger.error(f"Typesense search failed: {e}", exc_info=True)
                raise StorageQueryError(f"Search failed: {e}") from e

        raise AssertionError("Unreachable")

    async def delete(self, id: str) -> bool:
        """Delete document by ID"""
        async with OperationTimer(self.metrics, "delete"):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")

            try:
                response = await self.client.delete(
                    f"{self.url}/collections/{self.collection_name}/documents/{id}"
                )
                return bool(response.status_code == 200)
            except Exception as e:
                logger.error(f"Typesense delete failed: {e}", exc_info=True)
                return False

        raise AssertionError("Unreachable")

    # Batch operations (optimized for Typesense)

    async def store_batch(self, items: list[dict[str, Any]]) -> list[str]:
        """
        Index multiple documents in a single batch operation.

        More efficient than calling store() multiple times as it uses
        Typesense's batch import capability.

        Args:
            items: List of document data dictionaries

        Returns:
            List of document IDs in same order as input

        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If batch operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Typesense")

        if not items:
            return []

        try:
            # Ensure all items have IDs
            ids = []
            documents = []
            for item in items:
                if "id" not in item:
                    item = item.copy()
                    item["id"] = str(uuid.uuid4())
                ids.append(item["id"])
                documents.append(item)

            # Batch import using newline-delimited JSON
            import_data = "\n".join(json.dumps(doc) for doc in documents)

            response = await self.client.post(
                f"{self.url}/collections/{self.collection_name}/documents/import",
                content=import_data,
                headers={"Content-Type": "text/plain"},
            )
            await self._raise_for_status(response)

            logger.debug(f"Indexed {len(documents)} documents in batch")
            return ids

        except httpx.HTTPStatusError as e:
            logger.error(f"Typesense batch store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Batch store failed: {e}") from e
        except Exception as e:
            logger.error(f"Typesense batch store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Batch store failed: {e}") from e

    async def retrieve_batch(self, ids: list[str]) -> list[dict[str, Any] | None]:
        """
        Retrieve multiple documents by their IDs.

        Note: Typesense doesn't have a native batch retrieve endpoint,
        so this uses the default implementation (sequential retrieves).

        Args:
            ids: List of document identifiers

        Returns:
            List of data dictionaries (None for not found items)

        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If batch operation fails
        """
        # Use default implementation from base class
        # (Typesense doesn't have batch retrieve API)
        return await super().retrieve_batch(ids)

    async def delete_batch(self, ids: list[str]) -> dict[str, bool]:
        """
        Delete multiple documents by their IDs.

        More efficient than calling delete() multiple times as it uses
        filter-based batch deletion.

        Args:
            ids: List of document identifiers to delete

        Returns:
            Dictionary mapping IDs to deletion status

        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If batch operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Typesense")

        if not ids:
            return {}

        try:
            # Typesense supports filter-based deletion
            # Build filter for all IDs: id:=[id1,id2,id3]
            filter_str = f"id:=[{','.join(ids)}]"

            response = await self.client.delete(
                f"{self.url}/collections/{self.collection_name}/documents",
                params={"filter_by": filter_str},
            )

            if response.status_code == 200:
                # All deletions successful
                results = {id: True for id in ids}
                logger.debug(f"Deleted {len(ids)} documents in batch")
            else:
                # Fallback to individual deletions if batch fails
                results = {}
                for id in ids:
                    try:
                        del_response = await self.client.delete(
                            f"{self.url}/collections/{self.collection_name}/documents/{id}"
                        )
                        results[id] = del_response.status_code == 200
                    except Exception:
                        results[id] = False

                deleted_count = sum(1 for v in results.values() if v)
                logger.debug(f"Deleted {deleted_count} of {len(ids)} documents")

            return results

        except Exception as e:
            logger.error(f"Typesense batch delete failed: {e}", exc_info=True)
            raise StorageQueryError(f"Batch delete failed: {e}") from e

        raise AssertionError("Unreachable")

    async def health_check(self) -> dict[str, Any]:
        """
        Check Typesense backend health and performance.

        Performs actual connectivity test and measures latency.

        Returns:
            Dictionary with health status including:
            - status: 'healthy', 'degraded', or 'unhealthy'
            - connected: Connection status
            - latency_ms: Response time in milliseconds
            - collection_exists: Whether collection is available
            - document_count: Number of documents in collection
            - details: Additional information
            - timestamp: ISO timestamp
        """
        import time
        from datetime import datetime

        start_time = time.perf_counter()

        try:
            if not self._connected or not self.client:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "details": "Not connected to Typesense",
                    "timestamp": datetime.now(UTC).isoformat(),
                }

            # Get collection info to verify connectivity
            response = await self.client.get(f"{self.url}/collections/{self.collection_name}")
            await self._raise_for_status(response)

            collection_info = await self._response_json(response)
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Determine health status based on latency
            if latency_ms < 100:
                status = "healthy"
            elif latency_ms < 500:
                status = "degraded"
            else:
                status = "unhealthy"
            if self._schema_warnings and status == "healthy":
                status = "degraded"

            return {
                "status": status,
                "connected": True,
                "latency_ms": round(latency_ms, 2),
                "collection_exists": True,
                "collection_name": self.collection_name,
                "document_count": collection_info.get("num_documents", 0),
                "schema_status": "degraded" if self._schema_warnings else "ok",
                "schema_warnings": list(self._schema_warnings),
                "details": f'Typesense collection "{self.collection_name}" is accessible',
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except httpx.HTTPStatusError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Typesense health check failed: {e}", exc_info=True)

            return {
                "status": "unhealthy",
                "connected": self._connected,
                "latency_ms": round(latency_ms, 2),
                "details": f"Health check failed: {e!s}",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Typesense health check failed: {e}", exc_info=True)

            return {
                "status": "unhealthy",
                "connected": self._connected,
                "latency_ms": round(latency_ms, 2),
                "details": f"Health check failed: {e!s}",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        raise AssertionError("Unreachable")

    async def _get_backend_metrics(self) -> dict[str, Any] | None:
        """Get Typesense-specific metrics."""
        if not self._connected or not self.client:
            return None

        try:
            response = await self.client.get(f"{self.url}/collections/{self.collection_name}")
            await self._raise_for_status(response)
            collection = await self._response_json(response)
            return {
                "document_count": collection.get("num_documents", 0),
                "collection_name": self.collection_name,
                "schema_fields": len(collection.get("fields", [])),
                "schema_status": "degraded" if self._schema_warnings else "ok",
            }
        except Exception as e:
            logger.error(f"Failed to get backend metrics: {e}")
            return {"error": str(e)}
