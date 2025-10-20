"""
Redis storage adapter for high-speed active context caching.

This adapter provides sub-millisecond read access to recent conversation
turns using Redis lists with automatic TTL and windowing for recent conversation turns.

Features:
- Session-based key namespacing
- List-based storage for conversation turns
- Automatic TTL (24 hours)
- Window size limiting (keep only N recent turns)
- Pipeline operations for batch writes
- JSON serialization for complex data

Key Design:
- Key format: session:{session_id}:turns
- Data structure: Redis LIST (FIFO with limited size)
- TTL: 24 hours (auto-renewed on access)

Performance Characteristics (measured on Redis 7.0, localhost, Python 3.13):
- Store latency (pipeline):  0.27ms mean (P50: 0.26ms, P95: 0.34ms, P99: 0.40ms)
- Retrieve latency:          0.24ms mean (P50: 0.24ms, P95: 0.27ms, P99: 0.38ms)
- Search latency (10 items): 0.24ms mean (P50: 0.24ms, P95: 0.30ms, P99: 0.32ms)
- Session size query:        0.13ms mean (P50: 0.11ms, P95: 0.20ms, P99: 0.56ms)
- Delete operation:          0.15ms mean
- Throughput:                3400+ ops/sec (single connection)

All operations meet sub-millisecond targets. Benchmarks confirm excellent
performance for high-frequency caching workloads.

Benchmarks run with: pytest tests/benchmarks/bench_redis_adapter.py -v -s
"""

import redis.asyncio as redis
from redis.asyncio import Redis
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime, timezone

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
    StorageTimeoutError,
    validate_required_fields,
)

logger = logging.getLogger(__name__)


class RedisAdapter(StorageAdapter):
    """
    Redis adapter for high-speed active context caching (L1 memory).
    
    This adapter uses Redis LIST data structure to store recent conversation
    turns with automatic windowing (keeping only N most recent) and TTL
    management (24-hour expiration).
    
    Key Features:
    - Sub-millisecond read latency
    - Automatic window size limiting
    - TTL auto-renewal on access
    - JSON serialization for metadata
    - Pipeline support for batch operations
    
    Configuration:
        {
            'url': 'redis://host:port/db',
            'host': 'localhost',  # Alternative to url
            'port': 6379,         # Alternative to url
            'db': 0,              # Database number
            'password': None,     # Optional password
            'socket_timeout': 5,  # Connection timeout
            'window_size': 10,    # Max turns to keep
            'ttl_seconds': 86400, # 24 hours
            'refresh_ttl_on_read': False  # Extend TTL on read operations
        }
    
    TTL Behavior:
        - refresh_ttl_on_read=False (default): TTL expires 24h after last write
          Best for: Write-heavy workloads, sessions that should expire naturally
        
        - refresh_ttl_on_read=True: TTL extends on every read (retrieve/search)
          Best for: Read-heavy workloads, keeping active sessions "hot"
          Effect: Frequently accessed sessions stay cached indefinitely
    
    Data Structure:
        Key: session:{session_id}:turns
        Type: LIST
        Value: JSON-encoded turn data
        
        Example:
        session:abc123:turns -> [
            '{"turn_id": 3, "content": "Latest", "timestamp": "2025-10-20T10:03:00"}',
            '{"turn_id": 2, "content": "Middle", "timestamp": "2025-10-20T10:02:00"}',
            '{"turn_id": 1, "content": "Oldest", "timestamp": "2025-10-20T10:01:00"}'
        ]
    
    Example Usage:
        ```python
        config = {
            'url': 'redis://localhost:6379/0',
            'window_size': 10
        }
        
        adapter = RedisAdapter(config)
        await adapter.connect()
        
        # Store a turn (automatically added to session list)
        await adapter.store({
            'session_id': 'session-123',
            'turn_id': 1,
            'content': 'Hello!',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Get recent turns (from cache)
        turns = await adapter.search({
            'session_id': 'session-123',
            'limit': 5
        })
        
        await adapter.disconnect()
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Redis adapter.
        
        Args:
            config: Configuration dictionary with:
                - url: Redis connection URL (optional if host/port provided)
                - host: Redis host (default: 'localhost')
                - port: Redis port (default: 6379)
                - db: Database number (default: 0)
                - password: Optional password
                - socket_timeout: Connection timeout (default: 5)
                - window_size: Max turns per session (default: 10)
                - ttl_seconds: Key expiration (default: 86400 = 24h)
                - refresh_ttl_on_read: Refresh TTL on read operations (default: False)
        """
        super().__init__(config)
        
        # Connection config
        self.url = config.get('url')
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 6379)
        self.db = config.get('db', 0)
        self.password = config.get('password')
        self.socket_timeout = config.get('socket_timeout', 5)
        
        # Cache behavior config
        self.window_size = config.get('window_size', 10)
        self.ttl_seconds = config.get('ttl_seconds', 86400)  # 24 hours
        self.refresh_ttl_on_read = config.get('refresh_ttl_on_read', False)
        
        self.client: Optional[Redis] = None
        
        logger.info(
            f"RedisAdapter initialized (window: {self.window_size}, "
            f"TTL: {self.ttl_seconds}s, refresh_on_read: {self.refresh_ttl_on_read})"
        )
    
    async def connect(self) -> None:
        """
        Establish connection to Redis server.
        
        Creates async Redis client and verifies connectivity with PING.
        
        Raises:
            StorageConnectionError: If connection fails
            StorageTimeoutError: If connection times out
        """
        if self._connected and self.client:
            logger.warning("Already connected to Redis")
            return
        
        try:
            # Create Redis client from URL or host/port
            if self.url:
                self.client = await redis.from_url(
                    self.url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_timeout
                )
            else:
                self.client = Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_timeout
                )
            
            # Verify connection with PING
            pong = await self.client.ping()
            if not pong:
                raise StorageConnectionError("Redis PING failed")
            
            self._connected = True
            logger.info(f"Connected to Redis at {self.host}:{self.port}/{self.db}")
            
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}", exc_info=True)
            raise StorageConnectionError(
                f"Failed to connect to Redis: {e}"
            ) from e
        except redis.TimeoutError as e:
            logger.error(f"Redis connection timeout: {e}", exc_info=True)
            raise StorageTimeoutError(
                f"Connection timeout: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}", exc_info=True)
            raise StorageConnectionError(
                f"Redis connection failed: {e}"
            ) from e
    
    async def disconnect(self) -> None:
        """
        Close Redis connection and cleanup resources.
        
        Safe to call multiple times (idempotent).
        """
        if not self.client:
            logger.warning("No active Redis connection")
            return
        
        try:
            await self.client.aclose()
            self.client = None
            self._connected = False
            logger.info("Disconnected from Redis")
        except Exception as e:
            logger.error(f"Error during Redis disconnect: {e}", exc_info=True)
            # Don't raise - disconnect should always succeed
    
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store conversation turn in session's Redis list.
        
        Behavior:
        1. Serialize turn data to JSON
        2. Add to head of session list (LPUSH)
        3. Trim list to window_size (keep only N recent)
        4. Set TTL on key (24 hours)
        
        Required fields:
            - session_id: Session identifier
            - turn_id: Turn number
            - content: Turn content/message
        
        Optional fields:
            - timestamp: ISO format timestamp
            - metadata: Additional data
        
        Args:
            data: Dictionary with turn data
        
        Returns:
            String identifier in format "session:{id}:turns:{turn_id}"
        
        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If required fields missing
            StorageQueryError: If Redis operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        # Validate required fields
        validate_required_fields(data, ['session_id', 'turn_id', 'content'])
        
        try:
            session_id = data['session_id']
            turn_id = data['turn_id']
            key = self._make_key(session_id)
            
            # Prepare turn data for storage
            turn_data = {
                'turn_id': turn_id,
                'content': data['content'],
                'timestamp': data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                'metadata': data.get('metadata', {})
            }
            
            # Serialize to JSON
            serialized = json.dumps(turn_data)
            
            # Use pipeline for atomic operations
            async with self.client.pipeline(transaction=True) as pipe:
                # Add to head of list (most recent first)
                await pipe.lpush(key, serialized)
                
                # Trim to window size (keep only N most recent)
                await pipe.ltrim(key, 0, self.window_size - 1)
                
                # Set/refresh TTL
                await pipe.expire(key, self.ttl_seconds)
                
                # Execute pipeline
                await pipe.execute()
            
            # Generate ID for this turn
            record_id = f"{key}:{turn_id}"
            
            logger.debug(
                f"Stored turn {turn_id} in session {session_id} "
                f"(key: {key})"
            )
            
            return record_id
            
        except redis.RedisError as e:
            logger.error(f"Redis store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to store in Redis: {e}") from e
        except json.JSONEncodeError as e:
            logger.error(f"JSON encoding failed: {e}", exc_info=True)
            raise StorageDataError(f"Failed to encode data: {e}") from e
    
    def _make_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"session:{session_id}:turns"
    
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve specific turn from session list.
        
        If refresh_ttl_on_read is enabled, extends session TTL on access.
        
        ID format: "session:{session_id}:turns:{turn_id}"
        
        Args:
            id: Turn identifier from store()
        
        Returns:
            Dictionary with turn data, or None if not found
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If Redis operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            # Parse ID to extract key and turn_id
            # Format: session:{id}:turns:{turn_id}
            parts = id.rsplit(':', 1)
            if len(parts) != 2:
                raise StorageDataError(f"Invalid ID format: {id}")
            
            key = parts[0]
            turn_id = int(parts[1])
            
            # Get all items from list
            items = await self.client.lrange(key, 0, -1)
            
            # Optional: Refresh TTL on access
            if self.refresh_ttl_on_read and items:
                await self.client.expire(key, self.ttl_seconds)
                logger.debug(f"Refreshed TTL for {key} (read access)")
            
            # Search for matching turn_id
            for item in items:
                turn_data = json.loads(item)
                if turn_data.get('turn_id') == turn_id:
                    logger.debug(f"Retrieved turn {turn_id} from {key}")
                    return turn_data
            
            logger.debug(f"Turn {turn_id} not found in {key}")
            return None
            
        except redis.RedisError as e:
            logger.error(f"Redis retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to retrieve from Redis: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed: {e}", exc_info=True)
            raise StorageDataError(f"Failed to decode data: {e}") from e
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid ID format: {e}", exc_info=True)
            raise StorageDataError(f"Invalid ID: {id}") from e
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get recent turns for a session.
        
        If refresh_ttl_on_read is enabled, extends session TTL on access.
        
        Query parameters:
            - session_id: Session identifier (required)
            - limit: Maximum turns to return (default: window_size)
            - offset: Skip N turns (default: 0)
        
        Returns turns in reverse chronological order (most recent first).
        
        Args:
            query: Search parameters
        
        Returns:
            List of turn dictionaries
        
        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If session_id missing
            StorageQueryError: If Redis operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        # Validate required query parameters
        if 'session_id' not in query:
            raise StorageDataError("session_id required in query")
        
        try:
            session_id = query['session_id']
            key = self._make_key(session_id)
            
            # Get pagination parameters
            limit = query.get('limit', self.window_size)
            offset = query.get('offset', 0)
            
            # Calculate range (Redis uses 0-based indexing)
            start = offset
            end = offset + limit - 1
            
            # Get items from list
            items = await self.client.lrange(key, start, end)
            
            if not items:
                logger.debug(f"No turns found for session {session_id}")
                return []
            
            # Optional: Refresh TTL on access
            if self.refresh_ttl_on_read:
                await self.client.expire(key, self.ttl_seconds)
                logger.debug(f"Refreshed TTL for {key} (read access)")
            
            # Deserialize all items
            results = []
            for item in items:
                turn_data = json.loads(item)
                results.append(turn_data)
            
            logger.debug(
                f"Retrieved {len(results)} turns for session {session_id} "
                f"(limit: {limit}, offset: {offset})"
            )
            
            return results
            
        except redis.RedisError as e:
            logger.error(f"Redis search failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to search Redis: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed: {e}", exc_info=True)
            raise StorageDataError(f"Failed to decode data: {e}") from e
    
    async def delete(self, id: str) -> bool:
        """
        Delete entire session cache or specific turn.
        
        If id is in format "session:{id}:turns:{turn_id}", deletes specific turn.
        If id is in format "session:{id}:turns", deletes entire session cache.
        
        Args:
            id: Session key or turn identifier
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If Redis operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            # Check if deleting specific turn or entire session
            if id.count(':') == 3:
                # Specific turn: session:{id}:turns:{turn_id}
                return await self._delete_turn(id)
            else:
                # Entire session: session:{id}:turns
                key = id if ':' in id else self._make_key(id)
                result = await self.client.delete(key)
                deleted = result > 0
                
                if deleted:
                    logger.debug(f"Deleted session cache: {key}")
                
                return deleted
                
        except redis.RedisError as e:
            logger.error(f"Redis delete failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to delete from Redis: {e}") from e
    
    async def _delete_turn(self, id: str) -> bool:
        """Delete specific turn from session list"""
        # Parse ID
        parts = id.rsplit(':', 1)
        key = parts[0]
        turn_id = int(parts[1])
        
        # Get all items
        items = await self.client.lrange(key, 0, -1)
        
        # Find and remove matching turn
        for item in items:
            turn_data = json.loads(item)
            if turn_data.get('turn_id') == turn_id:
                # Remove this item from list
                removed = await self.client.lrem(key, 1, item)
                if removed > 0:
                    logger.debug(f"Deleted turn {turn_id} from {key}")
                    return True
        
        return False
    
    async def clear_session(self, session_id: str) -> bool:
        """
        Clear all cached turns for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if cache existed and was cleared
        """
        key = self._make_key(session_id)
        return await self.delete(key)
    
    async def get_session_size(self, session_id: str) -> int:
        """
        Get number of cached turns for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Number of turns in cache
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            key = self._make_key(session_id)
            size = await self.client.llen(key)
            return size
        except redis.RedisError as e:
            logger.error(f"Failed to get session size: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to get size: {e}") from e
    
    async def session_exists(self, session_id: str) -> bool:
        """
        Check if session has cached turns.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if session cache exists
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            key = self._make_key(session_id)
            exists = await self.client.exists(key)
            return exists > 0
        except redis.RedisError as e:
            logger.error(f"Failed to check session existence: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to check existence: {e}") from e
    
    async def refresh_ttl(self, session_id: str) -> bool:
        """
        Refresh TTL for session cache (extend expiration).
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if TTL was refreshed
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            key = self._make_key(session_id)
            result = await self.client.expire(key, self.ttl_seconds)
            return result
        except redis.RedisError as e:
            logger.error(f"Failed to refresh TTL: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to refresh TTL: {e}") from e