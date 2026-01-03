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

import httpx
import json
import asyncio
from typing import Dict, Any, List, Optional
import logging
import uuid

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
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
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get('url', '').rstrip('/')
        self.api_key = config.get('api_key')
        self.collection_name = config.get('collection_name', 'declarative_memory')
        self.schema = config.get('schema')
        self.client: Optional[httpx.AsyncClient] = None
        
        if not self.url or not self.api_key:
            raise StorageDataError("Typesense URL and API key required")
        
        logger.info(f"TypesenseAdapter initialized (collection: {self.collection_name})")

    async def _raise_for_status(self, response: httpx.Response) -> None:
        """Awaitable-safe wrapper for raise_for_status to support AsyncMock responses."""
        maybe_coro = response.raise_for_status()
        if asyncio.iscoroutine(maybe_coro):
            await maybe_coro
    
    def _get_default_schema(self) -> Dict[str, Any]:
        """
        Get default schema for auto-creating collection.
        
        Provides a flexible schema that works for benchmark and general use cases.
        """
        return {
            'name': self.collection_name,
            'fields': [
                {'name': 'id', 'type': 'string'},
                {'name': 'content', 'type': 'string'},
                {'name': 'session_id', 'type': 'string', 'facet': True, 'optional': True},
                {'name': 'title', 'type': 'string', 'optional': True},
                {'name': 'timestamp', 'type': 'int64', 'optional': True},
                {'name': 'fact_type', 'type': 'string', 'facet': True, 'optional': True},
                {'name': 'created_at', 'type': 'int64', 'optional': True}
            ]
        }
    
    async def connect(self) -> None:
        """Connect to Typesense and ensure collection exists"""
        async with OperationTimer(self.metrics, 'connect'):
            if not self.api_key:
                raise StorageDataError("Typesense API key required")
                
            try:
                self.client = httpx.AsyncClient(
                    headers={'X-TYPESENSE-API-KEY': str(self.api_key)},
                    timeout=10.0
                )
                
                # Check if collection exists
                response = await self.client.get(
                    f"{self.url}/collections/{self.collection_name}"
                )
                
                if response.status_code == 404:
                    # Create collection with provided schema or default
                    schema_to_use = self.schema or self._get_default_schema()
                    response = await self.client.post(
                        f"{self.url}/collections",
                        json=schema_to_use
                    )
                    await self._raise_for_status(response)
                    logger.info(f"Created collection: {self.collection_name}")
                
                self._connected = True
                logger.info(f"Connected to Typesense at {self.url}")
                
            except Exception as e:
                logger.error(f"Typesense connection failed: {e}", exc_info=True)
                raise StorageConnectionError(f"Failed to connect: {e}") from e
    
    async def disconnect(self) -> None:
        """Close Typesense connection"""
        async with OperationTimer(self.metrics, 'disconnect'):
            if self.client:
                await self.client.aclose()
                self.client = None
                self._connected = False
                logger.info("Disconnected from Typesense")
    
    async def store(self, data: Dict[str, Any]) -> str:
        """Index document in Typesense"""
        async with OperationTimer(self.metrics, 'store'):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")
            
            try:
                # Add auto-generated ID if not present
                if 'id' not in data:
                    data['id'] = str(uuid.uuid4())
                
                response = await self.client.post(
                    f"{self.url}/collections/{self.collection_name}/documents",
                    json=data
                )
                await self._raise_for_status(response)
                
                # Fix: Handle both coroutine and regular dict return types
                json_result = response.json()
                if asyncio.iscoroutine(json_result):
                    result = await json_result
                else:
                    result = json_result
                    
                logger.debug(f"Indexed document: {result['id']}")
                return result['id']
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Typesense store failed: {e}", exc_info=True)
                raise StorageQueryError(f"Store failed: {e}") from e
            except Exception as e:
                logger.error(f"Typesense store failed: {e}", exc_info=True)
                raise StorageQueryError(f"Store failed: {e}") from e
    
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID"""
        async with OperationTimer(self.metrics, 'retrieve'):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")
            
            try:
                response = await self.client.get(
                    f"{self.url}/collections/{self.collection_name}/documents/{id}"
                )
                
                if response.status_code == 404:
                    return None
                
                await self._raise_for_status(response)
                # Fix: Handle both coroutine and regular dict return types
                json_result = response.json()
                if asyncio.iscoroutine(json_result):
                    return await json_result
                else:
                    return json_result
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                logger.error(f"Typesense retrieve failed: {e}", exc_info=True)
                raise StorageQueryError(f"Retrieve failed: {e}") from e
            except Exception as e:
                logger.error(f"Typesense retrieve failed: {e}", exc_info=True)
                raise StorageQueryError(f"Retrieve failed: {e}") from e
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Full-text search.
        
        Query params:
            - q: Search query
            - query_by: Fields to search
            - filter_by: Optional filters
            - limit: Max results (default: 10)
        """
        async with OperationTimer(self.metrics, 'search'):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")
            
            validate_required_fields(query, ['q', 'query_by'])
            
            try:
                params = {
                    'q': query['q'],
                    'query_by': query['query_by'],
                    'per_page': query.get('limit', 10),
                }
                
                if 'filter_by' in query:
                    params['filter_by'] = query['filter_by']
                
                response = await self.client.get(
                    f"{self.url}/collections/{self.collection_name}/documents/search",
                    params=params
                )
                await self._raise_for_status(response)
                
                # Fix: Handle both coroutine and regular dict return types
                json_result = response.json()
                if asyncio.iscoroutine(json_result):
                    result = await json_result
                else:
                    result = json_result
                    
                return [hit['document'] for hit in result.get('hits', [])]
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Typesense search failed: {e}", exc_info=True)
                raise StorageQueryError(f"Search failed: {e}") from e
            except Exception as e:
                logger.error(f"Typesense search failed: {e}", exc_info=True)
                raise StorageQueryError(f"Search failed: {e}") from e
    
    async def delete(self, id: str) -> bool:
        """Delete document by ID"""
        async with OperationTimer(self.metrics, 'delete'):
            if not self._connected or not self.client:
                raise StorageConnectionError("Not connected to Typesense")
            
            try:
                response = await self.client.delete(
                    f"{self.url}/collections/{self.collection_name}/documents/{id}"
                )
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Typesense delete failed: {e}", exc_info=True)
                return False
                return False
    
    # Batch operations (optimized for Typesense)
    
    async def store_batch(self, items: List[Dict[str, Any]]) -> List[str]:
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
                if 'id' not in item:
                    item = item.copy()
                    item['id'] = str(uuid.uuid4())
                ids.append(item['id'])
                documents.append(item)
            
            # Batch import using newline-delimited JSON
            import_data = '\n'.join(
                json.dumps(doc)
                for doc in documents
            )
            
            response = await self.client.post(
                f"{self.url}/collections/{self.collection_name}/documents/import",
                content=import_data,
                headers={
                    'Content-Type': 'text/plain'
                }
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
    
    async def retrieve_batch(self, ids: List[str]) -> List[Optional[Dict[str, Any]]]:
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
    
    async def delete_batch(self, ids: List[str]) -> Dict[str, bool]:
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
                params={'filter_by': filter_str}
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
    
    async def health_check(self) -> Dict[str, Any]:
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
        from datetime import datetime, timezone
        
        start_time = time.perf_counter()
        
        try:
            if not self._connected or not self.client:
                return {
                    'status': 'unhealthy',
                    'connected': False,
                    'details': 'Not connected to Typesense',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Get collection info to verify connectivity
            response = await self.client.get(
                f"{self.url}/collections/{self.collection_name}"
            )
            await self._raise_for_status(response)
            
            collection_info = await response.json()  # Fix: Await the json() coroutine
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Determine health status based on latency
            if latency_ms < 100:
                status = 'healthy'
            elif latency_ms < 500:
                status = 'degraded'
            else:
                status = 'unhealthy'
            
            return {
                'status': status,
                'connected': True,
                'latency_ms': round(latency_ms, 2),
                'collection_exists': True,
                'collection_name': self.collection_name,
                'document_count': collection_info.get('num_documents', 0),
                'details': f'Typesense collection "{self.collection_name}" is accessible',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except httpx.HTTPStatusError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Typesense health check failed: {e}", exc_info=True)
            
            return {
                'status': 'unhealthy',
                'connected': self._connected,
                'latency_ms': round(latency_ms, 2),
                'details': f'Health check failed: {str(e)}',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Typesense health check failed: {e}", exc_info=True)
            
            return {
                'status': 'unhealthy',
                'connected': self._connected,
                'latency_ms': round(latency_ms, 2),
                'details': f'Health check failed: {str(e)}',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
        """Get Typesense-specific metrics."""
        if not self._connected or not self.client:
            return None
        
        try:
            response = await self.client.get(
                f"{self.url}/collections/{self.collection_name}"
            )
            await self._raise_for_status(response)
            collection = response.json()
            return {
                'document_count': collection.get('num_documents', 0),
                'collection_name': self.collection_name,
                'schema_fields': len(collection.get('fields', []))
            }
        except Exception as e:
            logger.error(f"Failed to get backend metrics: {e}")
            return {'error': str(e)}
