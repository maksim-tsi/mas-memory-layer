"""
Redis Streams consumer for lifecycle event coordination.

This module provides a durable, scalable event coordination system using
Redis Streams for L1→L2→L3→L4 lifecycle events. Uses consumer groups for
reliable delivery and acknowledgment tracking.

Key Features:
- Single global stream: {mas}:lifecycle (all sessions)
- Consumer groups for horizontal scaling
- Automatic retry of unacknowledged messages
- MAXLEN ~ 50000 retention (25-50MB RAM ceiling)
- Graceful handling of consumer failures

Architecture:
- Producer (Agents): Publish events via NamespaceManager.publish_lifecycle_event()
- Consumer (Engines): Subscribe via consumer groups, process, and ACK
- Safety Net: Wake-Up Sweep catches missed events (eventual consistency)

Consumer Groups:
- "consolidation-workers": L2→L3 processing
- "distillation-workers": L3→L4 processing

Performance:
- Durable vs Pub/Sub (ephemeral)
- Guaranteed delivery with ACK
- Scales horizontally with multiple consumers

References:
- docs/research/redis-stream-retention-policy.md
- docs/research/redis-global-local-stream.md
- docs/research/consolidation-hooks-and-signals.md
"""

import redis.asyncio as redis
from typing import Dict, Any, List, Optional, Callable, Awaitable
import json
import logging
import asyncio
from datetime import datetime, timezone

from .namespace import NamespaceManager

logger = logging.getLogger(__name__)


class LifecycleStreamConsumer:
    """
    Redis Streams consumer for lifecycle event coordination.
    
    Processes events from the global {mas}:lifecycle stream using consumer
    groups for reliable delivery and horizontal scaling.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        consumer_group: str,
        consumer_name: str,
        block_ms: int = 5000,
        batch_size: int = 10,
    ):
        """
        Initialize lifecycle stream consumer.
        
        Args:
            redis_client: Async Redis client
            consumer_group: Consumer group name (e.g., "consolidation-workers")
            consumer_name: Unique consumer name (e.g., "worker-1")
            block_ms: XREADGROUP block timeout in milliseconds (default: 5000)
            batch_size: Maximum messages to read per batch (default: 10)
        """
        self.redis = redis_client
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.block_ms = block_ms
        self.batch_size = batch_size
        self.stream_key = NamespaceManager.lifecycle_stream()
        self._running = False
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
    
    async def initialize(self) -> None:
        """
        Initialize consumer group (idempotent).
        
        Creates the consumer group if it doesn't exist. Safe to call multiple
        times - will succeed even if group already exists.
        
        Raises:
            redis.RedisError: If consumer group creation fails
        """
        try:
            # Create consumer group starting from beginning (0)
            # MKSTREAM creates the stream if it doesn't exist
            await self.redis.xgroup_create(
                name=self.stream_key,
                groupname=self.consumer_group,
                id="0",  # Start from beginning
                mkstream=True,
            )
            logger.info(
                f"Created consumer group: {self.consumer_group} "
                f"on stream {self.stream_key}"
            )
        
        except redis.ResponseError as e:
            # Group already exists - this is fine
            if "BUSYGROUP" in str(e):
                logger.debug(
                    f"Consumer group {self.consumer_group} already exists"
                )
            else:
                raise
    
    def register_handler(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:
        """
        Register an async handler for a specific event type.
        
        Args:
            event_type: Event type to handle (e.g., "promotion", "consolidation")
            handler: Async function that processes the event
            
        Example:
            async def handle_promotion(event: Dict[str, Any]):
                session_id = event["session_id"]
                data = json.loads(event["data"])
                # Process promotion...
            
            consumer.register_handler("promotion", handle_promotion)
        """
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    async def start(self) -> None:
        """
        Start consuming events from the stream.
        
        Runs an infinite loop that:
        1. Reads messages from the stream (XREADGROUP)
        2. Processes each message with registered handlers
        3. Acknowledges successful processing (XACK)
        4. Retries failed messages
        
        This method blocks until stop() is called.
        """
        self._running = True
        logger.info(
            f"Starting consumer: {self.consumer_name} "
            f"(group: {self.consumer_group})"
        )
        
        # Process any pending messages first (unacknowledged from previous run)
        await self._process_pending_messages()
        
        # Main event loop
        while self._running:
            try:
                # Read new messages (>) with blocking
                messages = await self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=self.batch_size,
                    block=self.block_ms,
                )
                
                if not messages:
                    # No new messages (timeout)
                    continue
                
                # Process each message
                for stream_key, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        await self._process_message(message_id, fields)
            
            except redis.RedisError as e:
                logger.error(f"Stream read error: {e}")
                await asyncio.sleep(1)  # Back off on error
            
            except Exception as e:
                logger.error(f"Unexpected error in consumer loop: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Consumer stopped: {self.consumer_name}")
    
    async def stop(self) -> None:
        """
        Stop consuming events.
        
        Sets the running flag to False, causing the start() loop to exit.
        """
        self._running = False
        logger.info(f"Stopping consumer: {self.consumer_name}")
    
    async def _process_pending_messages(self) -> None:
        """
        Process pending (unacknowledged) messages from previous runs.
        
        Uses XPENDING and XCLAIM to recover messages that were read but not
        acknowledged (e.g., due to consumer crash).
        """
        try:
            # Get pending messages for this consumer
            pending = await self.redis.xpending_range(
                name=self.stream_key,
                groupname=self.consumer_group,
                min="-",
                max="+",
                count=100,
                consumername=self.consumer_name,
            )
            
            if pending:
                logger.info(
                    f"Found {len(pending)} pending messages for {self.consumer_name}"
                )
                
                for msg in pending:
                    message_id = msg["message_id"]
                    
                    # Re-read the message
                    messages = await self.redis.xrange(
                        name=self.stream_key,
                        min=message_id,
                        max=message_id,
                    )
                    
                    if messages:
                        _, fields = messages[0]
                        await self._process_message(message_id, fields)
        
        except redis.RedisError as e:
            logger.error(f"Error processing pending messages: {e}")
    
    async def _process_message(
        self,
        message_id: str,
        fields: Dict[bytes, bytes],
    ) -> None:
        """
        Process a single message and acknowledge if successful.
        
        Args:
            message_id: Redis stream message ID
            fields: Message fields (event_type, session_id, timestamp, data)
        """
        try:
            # Decode fields
            event = {
                key.decode('utf-8') if isinstance(key, bytes) else key: 
                value.decode('utf-8') if isinstance(value, bytes) else value
                for key, value in fields.items()
            }
            
            event_type = event.get("type")
            session_id = event.get("session_id")
            
            logger.debug(
                f"Processing event: {event_type} "
                f"(session={session_id}, id={message_id})"
            )
            
            # Find and execute handler
            handler = self._handlers.get(event_type)
            
            if handler:
                await handler(event)
            else:
                logger.warning(
                    f"No handler registered for event type: {event_type}"
                )
            
            # Acknowledge successful processing
            await self.redis.xack(
                self.stream_key,
                self.consumer_group,
                message_id,
            )
            
            logger.debug(f"Acknowledged message: {message_id}")
        
        except Exception as e:
            logger.error(
                f"Failed to process message {message_id}: {e}. "
                "Message will be retried."
            )
            # Don't ACK - message will remain pending for retry
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check consumer health and stream status.
        
        Returns:
            Health check result with consumer and stream metrics
        """
        try:
            # Get stream info
            stream_info = await self.redis.xinfo_stream(self.stream_key)
            
            # Get consumer group info
            groups_info = await self.redis.xinfo_groups(self.stream_key)
            
            # Find our group
            our_group = None
            for group in groups_info:
                if group["name"].decode() == self.consumer_group:
                    our_group = group
                    break
            
            # Get pending count
            pending = await self.redis.xpending(
                self.stream_key,
                self.consumer_group,
            )
            
            return {
                "status": "healthy",
                "running": self._running,
                "consumer_name": self.consumer_name,
                "consumer_group": self.consumer_group,
                "stream_length": stream_info["length"],
                "pending_messages": pending["pending"],
                "registered_handlers": list(self._handlers.keys()),
                "group_info": {
                    "pending": our_group["pending"] if our_group else 0,
                    "consumers": our_group["consumers"] if our_group else 0,
                } if our_group else None,
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


class LifecycleStreamProducer:
    """
    Convenience wrapper for publishing lifecycle events.
    
    This is a thin wrapper around NamespaceManager.publish_lifecycle_event()
    for consistency with the consumer API.
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize lifecycle stream producer.
        
        Args:
            redis_client: Async Redis client
        """
        self.namespace_manager = NamespaceManager(redis_client)
    
    async def publish(
        self,
        event_type: str,
        session_id: str,
        data: Dict[str, Any],
    ) -> str:
        """
        Publish a lifecycle event to the global stream.
        
        Args:
            event_type: Event type (e.g., "promotion", "consolidation")
            session_id: Session ID that triggered the event
            data: Event payload (must be JSON-serializable)
            
        Returns:
            Event ID from Redis XADD
        """
        return await self.namespace_manager.publish_lifecycle_event(
            event_type=event_type,
            session_id=session_id,
            data=data,
        )
