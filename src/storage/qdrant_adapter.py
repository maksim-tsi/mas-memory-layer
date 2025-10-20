"""
Qdrant vector storage adapter for semantic memory (L3).

This adapter provides vector similarity search for distilled knowledge
and semantic relationships.

Features:
- Vector storage and retrieval
- Similarity search with score thresholds
- Metadata filtering
- Collection auto-management
"""

import uuid
from typing import Dict, Any, List, Optional
import logging
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
    validate_required_fields,
)

logger = logging.getLogger(__name__)


class QdrantAdapter(StorageAdapter):
    """
    Qdrant adapter for vector storage (L3 semantic memory).
    
    Configuration:
        {
            'url': 'http://host:port',
            'api_key': 'optional_api_key',
            'collection_name': 'semantic_memory',
            'vector_size': 384,  # Default for all-MiniLM-L6-v2
            'distance': 'Cosine'  # or 'Euclid', 'Dot'
        }
    
    Example:
        ```python
        config = {
            'url': 'http://192.168.107.187:6333',
            'collection_name': 'semantic_memory',
            'vector_size': 384
        }
        
        adapter = QdrantAdapter(config)
        await adapter.connect()
        
        # Store vector
        await adapter.store({
            'vector': [0.1, 0.2, 0.3, ...],  # 384-dimensional vector
            'content': 'User prefers dark mode',
            'session_id': 'session-123',
            'metadata': {'fact_type': 'preference'}
        })
        
        # Search similar vectors
        results = await adapter.search({
            'vector': [0.1, 0.2, 0.3, ...],
            'limit': 5,
            'score_threshold': 0.7,
            'filter': {'session_id': 'session-123'}
        })
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get('url')
        self.api_key = config.get('api_key')
        self.collection_name = config.get('collection_name', 'semantic_memory')
        self.vector_size = config.get('vector_size', 384)
        self.distance = config.get('distance', 'Cosine')
        self.client: Optional[AsyncQdrantClient] = None
        
        if not self.url:
            raise StorageDataError("Qdrant URL is required")
        
        logger.info(f"QdrantAdapter initialized (collection: {self.collection_name})")
    
    async def connect(self) -> None:
        """
        Connect to Qdrant and ensure collection exists.
        
        Creates collection if it doesn't exist with configured vector parameters.
        """
        if self._connected and self.client:
            logger.warning("Already connected to Qdrant")
            return
        
        try:
            # Create async client
            self.client = AsyncQdrantClient(
                url=self.url,
                api_key=self.api_key
            )
            
            # Check if collection exists
            try:
                await self.client.get_collection(self.collection_name)
            except Exception:
                # Collection doesn't exist, create it
                distance_map = {
                    'Cosine': Distance.COSINE,
                    'Euclid': Distance.EUCLID,
                    'Dot': Distance.DOT
                }
                
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=distance_map.get(self.distance, Distance.COSINE)
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            
            self._connected = True
            logger.info(f"Connected to Qdrant at {self.url}")
            
        except Exception as e:
            logger.error(f"Qdrant connection failed: {e}", exc_info=True)
            raise StorageConnectionError(f"Failed to connect to Qdrant: {e}") from e
    
    async def disconnect(self) -> None:
        """
        Close Qdrant connection.
        
        Safe to call multiple times (idempotent).
        """
        if not self.client:
            logger.warning("No active Qdrant connection")
            return
        
        try:
            await self.client.close()
            self.client = None
            self._connected = False
            logger.info("Disconnected from Qdrant")
        except Exception as e:
            logger.error(f"Error during Qdrant disconnect: {e}", exc_info=True)
            # Don't raise - disconnect should always succeed
    
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store vector embedding with payload.
        
        Required fields:
            - vector: List of floats (dimension must match collection)
            - content: Text content
        
        Optional fields:
            - id: Custom ID (default: auto-generated UUID)
            - metadata: Additional metadata dict
        
        Args:
            data: Dictionary with vector data and metadata
        
        Returns:
            String ID of stored point
        
        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If required fields missing or invalid
            StorageQueryError: If storage operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        # Validate required fields
        validate_required_fields(data, ['vector', 'content'])
        
        try:
            # Prepare point data
            point_id = data.get('id', str(uuid.uuid4()))
            vector = data['vector']
            payload = {
                'content': data['content'],
                'metadata': data.get('metadata', {}),
                'created_at': data.get('created_at')
            }
            
            # Add any additional top-level fields to payload
            for key, value in data.items():
                if key not in ['vector', 'content', 'id', 'metadata', 'created_at']:
                    payload[key] = value
            
            # Create point
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            
            # Store point
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.debug(f"Stored vector with ID: {point_id}")
            return str(point_id)
            
        except Exception as e:
            logger.error(f"Qdrant store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to store in Qdrant: {e}") from e
    
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve vector by ID.
        
        Args:
            id: Point identifier
        
        Returns:
            Dictionary with vector data, or None if not found
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If retrieval operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        try:
            # Retrieve point
            points = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[id]
            )
            
            if not points:
                logger.debug(f"Point {id} not found")
                return None
            
            point = points[0]
            result = {
                'id': str(point.id),
                'vector': point.vector,
                'content': point.payload.get('content'),
                'metadata': point.payload.get('metadata', {}),
            }
            
            # Add any additional payload fields
            for key, value in point.payload.items():
                if key not in ['content', 'metadata']:
                    result[key] = value
            
            logger.debug(f"Retrieved point {id}")
            return result
            
        except Exception as e:
            logger.error(f"Qdrant retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to retrieve from Qdrant: {e}") from e
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Query parameters:
            - vector: Query vector for similarity search
            - limit: Maximum results (default: 10)
            - score_threshold: Minimum similarity score (default: 0.0)
            - filter: Dict of field-value pairs for metadata filtering
        
        Args:
            query: Search parameters
        
        Returns:
            List of matching points with similarity scores
        
        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If vector missing
            StorageQueryError: If search operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        # Validate required fields
        validate_required_fields(query, ['vector'])
        
        try:
            # Get query parameters
            vector = query['vector']
            limit = query.get('limit', 10)
            score_threshold = query.get('score_threshold', 0.0)
            
            # Build filter if provided
            search_filter = None
            if 'filter' in query:
                must_conditions = []
                for field, value in query['filter'].items():
                    must_conditions.append(
                        FieldCondition(
                            key=field,
                            match=MatchValue(value=value)
                        )
                    )
                if must_conditions:
                    search_filter = Filter(must=must_conditions)
            
            # Perform search
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )
            
            # Format results
            formatted_results = []
            for hit in results:
                result = {
                    'id': str(hit.id),
                    'vector': hit.vector,
                    'content': hit.payload.get('content'),
                    'metadata': hit.payload.get('metadata', {}),
                    'score': hit.score
                }
                
                # Add any additional payload fields
                for key, value in hit.payload.items():
                    if key not in ['content', 'metadata']:
                        result[key] = value
                
                formatted_results.append(result)
            
            logger.debug(f"Search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to search Qdrant: {e}") from e
    
    async def delete(self, id: str) -> bool:
        """
        Delete vector by ID.
        
        Args:
            id: Point identifier
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If delete operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        try:
            # Delete point
            result = await self.client.delete(
                collection_name=self.collection_name,
                points_selector=[id]
            )
            
            deleted = result.status == "completed"
            if deleted:
                logger.debug(f"Deleted point {id}")
            else:
                logger.debug(f"Point {id} not found for deletion")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Qdrant delete failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to delete from Qdrant: {e}") from e
    
    # Batch operations (optimized for Qdrant)
    
    async def store_batch(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Store multiple vectors in a single batch operation.
        
        More efficient than calling store() multiple times as it uses
        Qdrant's batch upsert capability.
        
        Args:
            items: List of data dictionaries, each with 'vector' and 'content'
        
        Returns:
            List of point IDs in same order as input
        
        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If any item missing required fields
            StorageQueryError: If batch operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        if not items:
            return []
        
        # Validate all items have required fields
        for i, item in enumerate(items):
            try:
                validate_required_fields(item, ['vector', 'content'])
            except StorageDataError as e:
                raise StorageDataError(f"Item {i}: {e}") from e
        
        try:
            # Prepare all points
            points = []
            ids = []
            
            for item in items:
                point_id = item.get('id', str(uuid.uuid4()))
                ids.append(str(point_id))
                
                payload = {
                    'content': item['content'],
                    'metadata': item.get('metadata', {}),
                    'created_at': item.get('created_at')
                }
                
                # Add any additional top-level fields to payload
                for key, value in item.items():
                    if key not in ['vector', 'content', 'id', 'metadata', 'created_at']:
                        payload[key] = value
                
                point = PointStruct(
                    id=point_id,
                    vector=item['vector'],
                    payload=payload
                )
                points.append(point)
            
            # Batch upsert all points at once
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.debug(f"Stored {len(points)} vectors in batch")
            return ids
            
        except Exception as e:
            logger.error(f"Qdrant batch store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to batch store in Qdrant: {e}") from e
    
    async def retrieve_batch(self, ids: List[str]) -> List[Optional[Dict[str, Any]]]:
        """
        Retrieve multiple vectors by their IDs in a single operation.
        
        More efficient than calling retrieve() multiple times.
        
        Args:
            ids: List of point identifiers
        
        Returns:
            List of data dictionaries (None for not found items)
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If batch operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        if not ids:
            return []
        
        try:
            # Retrieve all points at once
            points = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=ids
            )
            
            # Create a mapping of ID to point for quick lookup
            points_map = {str(point.id): point for point in points}
            
            # Return results in same order as input IDs
            results = []
            for id in ids:
                if id in points_map:
                    point = points_map[id]
                    result = {
                        'id': str(point.id),
                        'vector': point.vector,
                        'content': point.payload.get('content'),
                        'metadata': point.payload.get('metadata', {}),
                    }
                    
                    # Add any additional payload fields
                    for key, value in point.payload.items():
                        if key not in ['content', 'metadata']:
                            result[key] = value
                    
                    results.append(result)
                else:
                    results.append(None)
            
            logger.debug(f"Retrieved {len([r for r in results if r])} of {len(ids)} vectors in batch")
            return results
            
        except Exception as e:
            logger.error(f"Qdrant batch retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to batch retrieve from Qdrant: {e}") from e
    
    async def delete_batch(self, ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple vectors by their IDs in a single operation.
        
        More efficient than calling delete() multiple times.
        
        Args:
            ids: List of point identifiers to delete
        
        Returns:
            Dictionary mapping IDs to deletion status
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If batch operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        if not ids:
            return {}
        
        try:
            # Delete all points at once
            result = await self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            
            # Qdrant doesn't tell us which specific IDs were deleted
            # Assume all were successful if operation completed
            success = result.status == "completed"
            results = {id: success for id in ids}
            
            if success:
                logger.debug(f"Deleted {len(ids)} vectors in batch")
            else:
                logger.debug(f"Batch delete incomplete for {len(ids)} vectors")
            
            return results
            
        except Exception as e:
            logger.error(f"Qdrant batch delete failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to batch delete from Qdrant: {e}") from e
