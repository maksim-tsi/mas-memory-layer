"""
Neo4j graph database adapter for episodic memory (L4).

This adapter provides graph storage for entities, relationships,
and temporal sequences.

Features:
- Entity and relationship storage
- Relationship management
- Cypher query execution
- Graph traversal operations
"""

from neo4j import AsyncGraphDatabase, AsyncDriver
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


class Neo4jAdapter(StorageAdapter):
    """
    Neo4j adapter for entity and relationship storage (L4).
    
    Configuration:
        {
            'uri': 'bolt://host:port',
            'user': 'neo4j',
            'password': 'password',
            'database': 'neo4j'  # Optional, default DB
        }
    
    Example:
        ```python
        config = {
            'uri': 'bolt://192.168.107.187:7687',
            'user': 'neo4j',
            'password': 'your_password'
        }
        
        adapter = Neo4jAdapter(config)
        await adapter.connect()
        
        # Store entity
        await adapter.store({
            'type': 'entity',
            'label': 'Person',
            'properties': {'name': 'Alice', 'age': 30}
        })
        
        # Store relationship
        await adapter.store({
            'type': 'relationship',
            'from': 'Alice',
            'to': 'Bob',
            'relationship': 'KNOWS',
            'properties': {'since': '2020'}
        })
        
        # Query relationships
        results = await adapter.search({
            'cypher': 'MATCH (p:Person)-[r:KNOWS]->(f) RETURN p, r, f',
            'params': {}
        })
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.uri: str = config.get('uri', '')
        self.user: str = config.get('user', 'neo4j')
        self.password: str = config.get('password', '')
        self.database: str = config.get('database', 'neo4j')
        self.driver: Optional[AsyncDriver] = None
        
        if not self.uri or not self.password:
            raise StorageDataError("Neo4j URI and password required")
        
        logger.info(f"Neo4jAdapter initialized (uri: {self.uri})")
    
    async def connect(self) -> None:
        """Connect to Neo4j database"""
        async with OperationTimer(self.metrics, 'connect'):
            if not self.uri or not self.password:
                raise StorageDataError("Neo4j URI and password required")
                
            try:
                self.driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password)
                )
                
                # Verify connection
                if self.driver is not None:
                    async with self.driver.session(database=self.database) as session:
                        result = await session.run("RETURN 1 AS test")
                        await result.single()
                
                self._connected = True
                logger.info(f"Connected to Neo4j at {self.uri}")
                
            except Exception as e:
                logger.error(f"Neo4j connection failed: {e}", exc_info=True)
                raise StorageConnectionError(f"Failed to connect: {e}") from e
    
    async def disconnect(self) -> None:
        """Close Neo4j connection"""
        async with OperationTimer(self.metrics, 'disconnect'):
            if self.driver:
                await self.driver.close()
                self.driver = None
                self._connected = False
                logger.info("Disconnected from Neo4j")

    async def execute_query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute arbitrary Cypher and return result data."""
        async with OperationTimer(self.metrics, 'execute_query'):
            if not self.driver:
                raise StorageConnectionError("Not connected to Neo4j")

            try:
                async with self.driver.session(database=self.database) as session:
                    result = await session.run(cypher, params or {})
                    return await result.data()
            except Exception as e:
                logger.error(f"Neo4j query failed: {e}", exc_info=True)
                raise StorageQueryError(f"Query failed: {e}") from e
    
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store entity or relationship.
        
        For entities:
            - type: 'entity'
            - label: Node label
            - properties: Dict of properties
        
        For relationships:
            - type: 'relationship'
            - from: Source node identifier
            - to: Target node identifier
            - relationship: Relationship type
            - properties: Dict of properties
        """
        async with OperationTimer(self.metrics, 'store'):
            if not self._connected or not self.driver:
                raise StorageConnectionError("Not connected to Neo4j")
            
            validate_required_fields(data, ['type'])
            
            try:
                if data['type'] == 'entity':
                    return await self._store_entity(data)
                elif data['type'] == 'relationship':
                    return await self._store_relationship(data)
                else:
                    raise StorageDataError(f"Unknown type: {data['type']}")
                    
            except Exception as e:
                logger.error(f"Neo4j store failed: {e}", exc_info=True)
                raise StorageQueryError(f"Store failed: {e}") from e
    
    async def _store_entity(self, data: Dict[str, Any]) -> str:
        """Store entity node"""
        if self.driver is None:
            raise StorageConnectionError("Not connected to Neo4j")
            
        validate_required_fields(data, ['label', 'properties'])
        
        label = data['label']
        props = data['properties']
        
        # Generate ID from name or use UUID
        node_id = props.get('name', str(uuid.uuid4()))
        props['id'] = node_id
        
        cypher = """
            MERGE (n:%s {id: $id})
            SET n += $props
            RETURN n.id AS id
        """ % label
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(cypher, id=node_id, props=props)
            record = await result.single()
            if record is None:
                raise StorageQueryError("Failed to store entity")
            return record['id']
    
    async def _store_relationship(self, data: Dict[str, Any]) -> str:
        """Store relationship between nodes"""
        if self.driver is None:
            raise StorageConnectionError("Not connected to Neo4j")
            
        validate_required_fields(data, ['from', 'to', 'relationship'])
        
        from_id = data['from']
        to_id = data['to']
        rel_type = data['relationship']
        props = data.get('properties', {})
        
        cypher = """
            MATCH (from {id: $from_id})
            MATCH (to {id: $to_id})
            MERGE (from)-[r:%s]->(to)
            SET r += $props
            RETURN id(r) AS id
        """ % rel_type
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                cypher,
                from_id=from_id,
                to_id=to_id,
                props=props
            )
            record = await result.single()
            if record is None:
                raise StorageQueryError("Failed to store relationship")
            return str(record['id'])
    
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve entity by ID"""
        async with OperationTimer(self.metrics, 'retrieve'):
            if not self._connected or not self.driver:
                raise StorageConnectionError("Not connected to Neo4j")
            
            try:
                cypher = "MATCH (n {id: $id}) RETURN n"
                
                if self.driver is not None:
                    async with self.driver.session(database=self.database) as session:
                        result = await session.run(cypher, id=id)
                        record = await result.single()
                        
                        if not record:
                            return None
                        
                        node = record['n']
                        return dict(node)
                return None
                    
            except Exception as e:
                logger.error(f"Neo4j retrieve failed: {e}", exc_info=True)
                raise StorageQueryError(f"Retrieve failed: {e}") from e
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute Cypher query.
        
        Query params:
            - cypher: Cypher query string
            - params: Query parameters (optional)
        """
        async with OperationTimer(self.metrics, 'search'):
            if not self._connected or not self.driver:
                raise StorageConnectionError("Not connected to Neo4j")
            
            validate_required_fields(query, ['cypher'])
            
            try:
                cypher = query['cypher']
                params = query.get('params', {})
                
                if self.driver is not None:
                    async with self.driver.session(database=self.database) as session:
                        result = await session.run(cypher, **params)
                        records = await result.data()
                        return records
                return []
                    
            except Exception as e:
                logger.error(f"Neo4j search failed: {e}", exc_info=True)
                raise StorageQueryError(f"Search failed: {e}") from e
    
    async def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        async with OperationTimer(self.metrics, 'delete'):
            if not self._connected or not self.driver:
                raise StorageConnectionError("Not connected to Neo4j")
            
            try:
                cypher = "MATCH (n {id: $id}) DETACH DELETE n"
                
                if self.driver is not None:
                    async with self.driver.session(database=self.database) as session:
                        result = await session.run(cypher, id=id)
                        summary = await result.consume()
                        return summary.counters.nodes_deleted > 0
                return False
                    
            except Exception as e:
                logger.error(f"Neo4j delete failed: {e}", exc_info=True)
                return False
                return False
    
    # Batch operations (optimized for Neo4j)
    
    async def store_batch(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Store multiple entities or relationships in a single transaction.
        
        More efficient than calling store() multiple times as it uses
        a single Neo4j transaction for all operations.
        
        Args:
            items: List of entity or relationship data dictionaries
        
        Returns:
            List of IDs in same order as input
        
        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If any item missing required fields
            StorageQueryError: If batch operation fails
        """
        if not self._connected or not self.driver:
            raise StorageConnectionError("Not connected to Neo4j")
        
        if not items:
            return []
        
        # Validate all items
        for i, item in enumerate(items):
            try:
                validate_required_fields(item, ['type'])
            except StorageDataError as e:
                raise StorageDataError(f"Item {i}: {e}") from e
        
        try:
            ids = []
            
            # Process all items in a single transaction
            async with self.driver.session(database=self.database) as session:
                async def _batch_store(tx):
                    batch_ids = []
                    for item in items:
                        if item['type'] == 'entity':
                            validate_required_fields(item, ['label', 'properties'])
                            label = item['label']
                            props = item['properties'].copy()
                            node_id = props.get('name', str(uuid.uuid4()))
                            props['id'] = node_id
                            
                            cypher = """
                                MERGE (n:%s {id: $id})
                                SET n += $props
                                RETURN n.id AS id
                            """ % label
                            
                            result = await tx.run(cypher, id=node_id, props=props)
                            record = await result.single()
                            batch_ids.append(record['id'] if record else node_id)
                            
                        elif item['type'] == 'relationship':
                            validate_required_fields(item, ['from', 'to', 'relationship'])
                            from_id = item['from']
                            to_id = item['to']
                            rel_type = item['relationship']
                            props = item.get('properties', {})
                            
                            cypher = """
                                MATCH (from {id: $from_id})
                                MATCH (to {id: $to_id})
                                MERGE (from)-[r:%s]->(to)
                                SET r += $props
                                RETURN id(r) AS id
                            """ % rel_type
                            
                            result = await tx.run(cypher, from_id=from_id, to_id=to_id, props=props)
                            record = await result.single()
                            batch_ids.append(str(record['id']) if record else '')
                        else:
                            raise StorageDataError(f"Unknown type: {item['type']}")
                    
                    return batch_ids
                
                ids = await session.execute_write(_batch_store)
            
            logger.debug(f"Stored {len(ids)} items in batch transaction")
            return ids
            
        except Exception as e:
            logger.error(f"Neo4j batch store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Batch store failed: {e}") from e
    
    async def retrieve_batch(self, ids: List[str]) -> List[Optional[Dict[str, Any]]]:
        """
        Retrieve multiple entities by their IDs in a single query.
        
        More efficient than calling retrieve() multiple times.
        
        Args:
            ids: List of entity identifiers
        
        Returns:
            List of data dictionaries (None for not found items)
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If batch operation fails
        """
        if not self._connected or not self.driver:
            raise StorageConnectionError("Not connected to Neo4j")
        
        if not ids:
            return []
        
        try:
            # Query all nodes at once
            cypher = "UNWIND $ids AS id MATCH (n {id: id}) RETURN id, n"
            
            async with self.driver.session(database=self.database) as session:
                result = await session.run(cypher, ids=ids)
                records = await result.data()
            
            # Create mapping of ID to node
            nodes_map = {record['id']: dict(record['n']) for record in records}
            
            # Return results in same order as input IDs
            results = [nodes_map.get(id) for id in ids]
            
            logger.debug(f"Retrieved {len([r for r in results if r])} of {len(ids)} entities in batch")
            return results
            
        except Exception as e:
            logger.error(f"Neo4j batch retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Batch retrieve failed: {e}") from e
    
    async def delete_batch(self, ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple entities by their IDs in a single transaction.
        
        More efficient than calling delete() multiple times.
        
        Args:
            ids: List of entity identifiers to delete
        
        Returns:
            Dictionary mapping IDs to deletion status
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If batch operation fails
        """
        if not self._connected or not self.driver:
            raise StorageConnectionError("Not connected to Neo4j")
        
        if not ids:
            return {}
        
        try:
            # Delete all nodes in a single query
            cypher = """
                UNWIND $ids AS id
                MATCH (n {id: id})
                DETACH DELETE n
                RETURN id, count(n) > 0 AS deleted
            """
            
            async with self.driver.session(database=self.database) as session:
                result = await session.run(cypher, ids=ids)
                records = await result.data()
            
            # Build results map
            results = {record['id']: record['deleted'] for record in records}
            
            # Add False for IDs not found
            for id in ids:
                if id not in results:
                    results[id] = False
            
            deleted_count = sum(1 for v in results.values() if v)
            logger.debug(f"Deleted {deleted_count} of {len(ids)} entities in batch")
            return results
            
        except Exception as e:
            logger.error(f"Neo4j batch delete failed: {e}", exc_info=True)
            raise StorageQueryError(f"Batch delete failed: {e}") from e
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Neo4j backend health and performance.
        
        Performs connectivity test and measures query latency.
        
        Returns:
            Dictionary with health status including:
            - status: 'healthy', 'degraded', or 'unhealthy'
            - connected: Connection status
            - latency_ms: Response time in milliseconds
            - node_count: Total number of nodes (if available)
            - relationship_count: Total number of relationships (if available)
            - database: Active database name
            - details: Additional information
            - timestamp: ISO timestamp
        """
        import time
        from datetime import datetime, timezone
        
        start_time = time.perf_counter()
        
        try:
            if not self._connected or not self.driver:
                return {
                    'status': 'unhealthy',
                    'connected': False,
                    'details': 'Not connected to Neo4j',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Execute simple query to check connectivity and get stats
            async with self.driver.session(database=self.database) as session:
                # Get node and relationship counts
                result = await session.run(
                    "MATCH (n) RETURN count(n) as node_count"
                )
                record = await result.single()
                node_count = record['node_count'] if record else 0
                
                result = await session.run(
                    "MATCH ()-[r]->() RETURN count(r) as rel_count"
                )
                record = await result.single()
                rel_count = record['rel_count'] if record else 0
            
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
                'database': self.database,
                'node_count': node_count,
                'relationship_count': rel_count,
                'details': f'Neo4j database "{self.database}" is accessible',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Neo4j health check failed: {e}", exc_info=True)
            
            return {
                'status': 'unhealthy',
                'connected': self._connected,
                'latency_ms': round(latency_ms, 2),
                'details': f'Health check failed: {str(e)}',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
        """Get Neo4j-specific metrics."""
        if not self._connected or not self.driver:
            return None
        
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run("""
                    MATCH (n)
                    RETURN count(n) AS node_count
                """)
                record = await result.single()
                
                return {
                    'node_count': record['node_count'] if record else 0,
                    'database_name': self.database
                }
        except Exception as e:
            logger.error(f"Failed to get backend metrics: {e}")
            return {'error': str(e)}
