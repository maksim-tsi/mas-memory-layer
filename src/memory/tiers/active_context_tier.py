"""
L1 Active Context Tier - Working Memory Buffer (ADR-003).

This module implements the L1 tier of the four-tier cognitive memory
architecture. It maintains a high-speed buffer of the most recent 10-20
conversational turns per session with automatic TTL expiration.

Architecture:
- Primary: Redis (hot cache for sub-millisecond access)
- Secondary: PostgreSQL (persistent backup for recovery)
- Pattern: Write-through cache with automatic windowing
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import json
import logging

from src.memory.tiers.base_tier import BaseTier, TierOperationError
from src.storage.base import StorageError, StorageDataError, validate_required_fields
from src.storage.redis_adapter import RedisAdapter
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.metrics.collector import MetricsCollector
from src.storage.metrics.timer import OperationTimer


logger = logging.getLogger(__name__)


class ActiveContextTier(BaseTier):
    """
    L1: Active Context - Working Memory Buffer.
    
    Maintains 10-20 most recent conversational turns per session.
    Uses Redis for speed, PostgreSQL for durability.
    Automatic TTL expiration after 24 hours.
    
    Key Features:
    - Turn windowing: Keeps only N most recent turns
    - TTL management: Auto-expires after 24 hours
    - Write-through cache: Redis (hot) + PostgreSQL (cold)
    - Graceful fallback: Falls back to PostgreSQL if Redis fails
    - Sub-millisecond latency: Target <5ms for retrieve operations
    
    Usage Example:
        ```python
        tier = ActiveContextTier(
            redis_adapter=redis,
            postgres_adapter=postgres,
            config={'window_size': 20, 'ttl_hours': 24}
        )
        await tier.initialize()
        
        # Store turn
        turn_id = await tier.store({
            'session_id': 'session-123',
            'turn_id': 'turn-001',
            'role': 'user',
            'content': 'Hello, world!',
            'timestamp': datetime.now(timezone.utc)
        })
        
        # Retrieve recent turns
        turns = await tier.retrieve('session-123')
        ```
    """
    
    # Default configuration
    DEFAULT_WINDOW_SIZE = 20
    DEFAULT_TTL_HOURS = 24
    REDIS_KEY_PREFIX = "l1:session:"
    
    def __init__(
        self,
        redis_adapter: RedisAdapter,
        postgres_adapter: PostgresAdapter,
        metrics_collector: Optional[MetricsCollector] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize L1 Active Context Tier.
        
        Args:
            redis_adapter: Redis adapter for hot cache
            postgres_adapter: PostgreSQL adapter for persistent storage
            metrics_collector: Optional metrics collector
            config: Optional configuration with keys:
                - window_size: Max turns per session (default: 20)
                - ttl_hours: TTL in hours (default: 24)
                - enable_postgres_backup: Store in PostgreSQL (default: True)
        """
        storage_adapters = {
            'redis': redis_adapter,
            'postgres': postgres_adapter
        }
        super().__init__(storage_adapters, metrics_collector, config)
        
        self.redis = redis_adapter
        self.postgres = postgres_adapter
        self.window_size = config.get('window_size', self.DEFAULT_WINDOW_SIZE) if config else self.DEFAULT_WINDOW_SIZE
        self.ttl_hours = config.get('ttl_hours', self.DEFAULT_TTL_HOURS) if config else self.DEFAULT_TTL_HOURS
        self.enable_postgres_backup = config.get('enable_postgres_backup', True) if config else True
        
        logger.info(
            f"L1 ActiveContextTier initialized: window_size={self.window_size}, "
            f"ttl_hours={self.ttl_hours}, postgres_backup={self.enable_postgres_backup}"
        )
    
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store a conversational turn in L1.
        
        Args:
            data: Turn data with required fields:
                - session_id: str - Session identifier
                - turn_id: str - Unique turn identifier
                - role: str - 'user' or 'assistant'
                - content: str - Turn content
                - timestamp: datetime (optional, defaults to utcnow)
                - metadata: Dict (optional, additional context)
        
        Returns:
            Unique turn identifier (turn_id)
        
        Raises:
            TierOperationError: If storage operation fails
            StorageDataError: If required fields are missing
        """
        async with OperationTimer(self.metrics, 'l1_store'):
            try:
                # Validate required fields
                required = ['session_id', 'turn_id', 'role', 'content']
                validate_required_fields(data, required)
                
                session_id = data['session_id']
                turn_id = data['turn_id']
                timestamp = data.get('timestamp', datetime.now(timezone.utc))
                
                logger.debug(f"Storing turn {turn_id} in session {session_id}")
                
                # Prepare turn data
                turn_data = {
                    'turn_id': turn_id,
                    'role': data['role'],
                    'content': data['content'],
                    'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
                    'metadata': data.get('metadata', {})
                }
                
                # Store in Redis (hot cache)
                redis_key = f"{self.REDIS_KEY_PREFIX}{session_id}"
                turn_json = json.dumps(turn_data)
                
                # Use Redis list operations for turn window
                # LPUSH: Add to front (most recent)
                await self.redis.lpush(redis_key, turn_json)
                
                # LTRIM: Keep only window_size most recent turns
                await self.redis.ltrim(redis_key, 0, self.window_size - 1)
                
                # Set TTL
                ttl_seconds = self.ttl_hours * 3600
                await self.redis.expire(redis_key, ttl_seconds)
                
                logger.debug(f"Stored turn {turn_id} in Redis with TTL {ttl_seconds}s")
                
                # Store in PostgreSQL (persistent backup)
                if self.enable_postgres_backup:
                    postgres_data = {
                        'session_id': session_id,
                        'turn_id': turn_id,
                        'role': data['role'],
                        'content': data['content'],
                        'timestamp': timestamp,
                        'tier': 'L1',
                        'metadata': json.dumps(data.get('metadata', {}))
                    }
                    await self.postgres.insert('active_context', postgres_data)
                    logger.debug(f"Stored turn {turn_id} in PostgreSQL backup")
                
                # Metrics are tracked by OperationTimer
                return turn_id
                
            except StorageDataError:
                # Re-raise validation errors as-is
                raise
            except Exception as e:
                logger.error(f"Failed to store turn in L1: {e}")
                raise TierOperationError(f"Failed to store turn: {e}") from e
    
    async def retrieve(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve recent turns for a session.
        
        Implements hot/cold cache pattern:
        1. Try Redis first (hot path - fast)
        2. Fallback to PostgreSQL (cold path - slower)
        3. Rebuild Redis cache if found in PostgreSQL
        
        Args:
            session_id: Session identifier
        
        Returns:
            List of recent turns (newest first) or None if not found
        """
        async with OperationTimer(self.metrics, 'l1_retrieve'):
            try:
                redis_key = f"{self.REDIS_KEY_PREFIX}{session_id}"
                
                logger.debug(f"Retrieving turns for session {session_id}")
                
                # Try Redis first (hot path)
                try:
                    turns_json = await self.redis.lrange(redis_key, 0, -1)
                    if turns_json:
                        turns = [json.loads(t) for t in turns_json]
                        logger.debug(f"Retrieved {len(turns)} turns from Redis (hot)")
                        return turns
                except Exception as redis_error:
                    logger.warning(f"Redis retrieval failed: {redis_error}, falling back to PostgreSQL")
                
                # Fallback to PostgreSQL (cold path)
                if self.enable_postgres_backup:
                    logger.debug(f"Attempting PostgreSQL fallback for session {session_id}")
                    postgres_result = await self.postgres.query(
                        table='active_context',
                        filters={'session_id': session_id, 'tier': 'L1'},
                        order_by='timestamp DESC',
                        limit=self.window_size
                    )
                    
                    if postgres_result:
                        logger.info(f"Retrieved {len(postgres_result)} turns from PostgreSQL (cold)")
                        
                        # Rebuild Redis cache
                        try:
                            for turn in reversed(postgres_result):
                                turn_data = {
                                    'turn_id': turn['turn_id'],
                                    'role': turn['role'],
                                    'content': turn['content'],
                                    'timestamp': turn['timestamp'].isoformat() if isinstance(turn['timestamp'], datetime) else turn['timestamp'],
                                    'metadata': json.loads(turn.get('metadata', '{}'))
                                }
                                await self.redis.lpush(redis_key, json.dumps(turn_data))
                            
                            # Set TTL
                            ttl_seconds = self.ttl_hours * 3600
                            await self.redis.expire(redis_key, ttl_seconds)
                            
                            logger.debug(f"Rebuilt Redis cache for session {session_id}")
                        except Exception as rebuild_error:
                            logger.warning(f"Failed to rebuild Redis cache: {rebuild_error}")
                        
                        return postgres_result
                
                # Not found in either storage
                logger.debug(f"Session {session_id} not found in L1")
                return None
                
            except Exception as e:
                logger.error(f"Failed to retrieve session from L1: {e}")
                raise TierOperationError(f"Failed to retrieve session: {e}") from e
    
    async def query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Query turns with filters.
        
        L1 queries always go to PostgreSQL for flexibility as they are
        typically used for administrative operations, not hot path retrieval.
        
        Args:
            filters: Query filters:
                - session_id: str (optional)
                - role: str (optional, 'user' or 'assistant')
                - timestamp_after: datetime (optional)
                - timestamp_before: datetime (optional)
            limit: Maximum results
            **kwargs: Additional query parameters
        
        Returns:
            List of matching turns (newest first)
        """
        async with OperationTimer(self.metrics, 'l1_query'):
            try:
                # Add L1 tier filter
                query_filters = {**(filters or {}), 'tier': 'L1'}
                
                result = await self.postgres.query(
                    table='active_context',
                    filters=query_filters,
                    order_by='timestamp DESC',
                    limit=limit
                )
                
                logger.debug(f"Query returned {len(result)} turns")
                return result
                
            except Exception as e:
                logger.error(f"Failed to query L1: {e}")
                raise TierOperationError(f"Failed to query L1: {e}") from e
    
    async def delete(self, session_id: str) -> bool:
        """
        Delete session from L1.
        
        Removes session from both Redis and PostgreSQL.
        
        Args:
            session_id: Session to delete
        
        Returns:
            True if deleted, False if not found
        """
        async with OperationTimer(self.metrics, 'l1_delete'):
            try:
                redis_key = f"{self.REDIS_KEY_PREFIX}{session_id}"
                deleted = False
                
                # Delete from Redis
                try:
                    redis_result = await self.redis.delete(redis_key)
                    if redis_result:
                        deleted = True
                        logger.debug(f"Deleted session {session_id} from Redis")
                except Exception as redis_error:
                    logger.warning(f"Redis deletion failed: {redis_error}")
                
                # Delete from PostgreSQL
                if self.enable_postgres_backup:
                    postgres_result = await self.postgres.delete(
                        'active_context',
                        filters={'session_id': session_id, 'tier': 'L1'}
                    )
                    if postgres_result:
                        deleted = True
                        logger.debug(f"Deleted session {session_id} from PostgreSQL")
                
                return deleted
                
            except Exception as e:
                logger.error(f"Failed to delete session from L1: {e}")
                raise TierOperationError(f"Failed to delete session: {e}") from e
    
    async def get_window_size(self, session_id: str) -> int:
        """
        Get current window size (number of turns) for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Number of turns currently stored
        """
        try:
            redis_key = f"{self.REDIS_KEY_PREFIX}{session_id}"
            size = await self.redis.llen(redis_key)
            return size
        except Exception as e:
            logger.error(f"Failed to get window size: {e}")
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of Redis and PostgreSQL.
        
        Returns:
            Health status with per-adapter details
        """
        try:
            redis_health = await self.redis.health_check()
            postgres_health = await self.postgres.health_check()
            
            # Overall status is healthy only if both are healthy
            overall_status = 'healthy' if (
                redis_health.get('status') == 'healthy' and
                postgres_health.get('status') == 'healthy'
            ) else 'degraded'
            
            return {
                'tier': 'L1_active_context',
                'status': overall_status,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'storage': {
                    'redis': redis_health,
                    'postgres': postgres_health
                },
                'config': {
                    'window_size': self.window_size,
                    'ttl_hours': self.ttl_hours,
                    'postgres_backup_enabled': self.enable_postgres_backup
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'tier': 'L1_active_context',
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
