"""
PostgreSQL storage adapter for active context and working memory.

This adapter uses psycopg (v3) with connection pooling for high-performance
async operations on the mas_memory database.

Database Tables:
- active_context: L1 memory (recent conversation turns, TTL: 24h)
- working_memory: L2 memory (session facts, TTL: 7 days)
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from psycopg import sql
from psycopg_pool import AsyncConnectionPool

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageDataError,
    StorageQueryError,
    StorageTimeoutError,
    validate_required_fields,
)

logger = logging.getLogger(__name__)


class PostgresAdapter(StorageAdapter):
    """
    PostgreSQL adapter for active context (L1) and working memory (L2).

    Features:
    - Connection pooling for high concurrency
    - Support for both active_context and working_memory tables
    - TTL-aware queries (automatic expiration filtering)
    - Parameterized queries (SQL injection protection)
    - Automatic reconnection on connection loss

    Configuration:
        {
            'url': 'postgresql://user:pass@host:port/database',
            'pool_size': 10,  # Maximum connections in pool
            'min_size': 2,    # Minimum connections to maintain
            'timeout': 5,     # Connection timeout in seconds
            'table': 'active_context'  # or 'working_memory'
        }

    Example:
        ```python
        config = {
            'url': os.getenv('POSTGRES_URL'),
            'pool_size': 10,
            'table': 'active_context'
        }
        adapter = PostgresAdapter(config)
        await adapter.connect()

        # Store a conversation turn
        turn_id = await adapter.store({
            'session_id': 'session-123',
            'turn_id': 1,
            'content': 'Hello, how can I help?',
            'metadata': {'role': 'assistant', 'tokens': 25}
        })

        # Retrieve recent turns
        turns = await adapter.search({
            'session_id': 'session-123',
            'limit': 10
        })

        await adapter.disconnect()
        ```
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize PostgreSQL adapter.

        Args:
            config: Configuration dictionary with:
                - url: PostgreSQL connection URL (required)
                - pool_size: Max connections (default: 10)
                - min_size: Min connections (default: 2)
                - timeout: Connection timeout (default: 5)
                - table: Target table name (default: 'active_context')
        """
        super().__init__(config)
        self.url: str = config.get("url", "")
        if not self.url:
            raise StorageDataError("PostgreSQL URL is required in config")

        self.pool_size = config.get("pool_size", 10)
        self.min_size = config.get("min_size", 2)
        self.timeout = config.get("timeout", 5)
        self.table = config.get("table", "active_context")
        self.lock_writes = bool(config.get("lock_writes", False))
        self.pool: AsyncConnectionPool | None = None

        logger.info(
            f"PostgresAdapter initialized for table '{self.table}' "
            f"(pool: {self.min_size}-{self.pool_size})"
        )

    async def connect(self) -> None:
        """
        Create connection pool to PostgreSQL.

        Establishes a connection pool with configured min/max size.
        Verifies connectivity by executing a test query.

        Raises:
            StorageConnectionError: If connection fails
            StorageTimeoutError: If connection times out
        """
        if self._connected and self.pool:
            logger.warning("Already connected, skipping")
            return

        try:
            # Create connection pool
            self.pool = AsyncConnectionPool(
                conninfo=self.url,
                min_size=self.min_size,
                max_size=self.pool_size,
                timeout=self.timeout,
                open=False,  # We'll open it manually
            )

            # Open the pool
            await self.pool.open()

            # Verify connection with test query
            async with self.pool.connection() as conn:
                result = await conn.execute("SELECT 1")
                await result.fetchone()

            self._connected = True
            logger.info(f"Connected to PostgreSQL (table: {self.table})")

        except psycopg.OperationalError as e:
            logger.error(f"PostgreSQL connection failed: {e}", exc_info=True)
            raise StorageConnectionError(f"Failed to connect to PostgreSQL: {e}") from e
        except TimeoutError as e:
            logger.error(f"PostgreSQL connection timeout: {e}", exc_info=True)
            raise StorageTimeoutError(f"Connection timeout: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}", exc_info=True)
            raise StorageConnectionError(f"Connection failed: {e}") from e

    async def disconnect(self) -> None:
        """
        Close connection pool and cleanup resources.

        Gracefully closes all connections in the pool.
        Safe to call multiple times (idempotent).
        """
        if not self.pool:
            logger.warning("No active connection pool")
            return

        try:
            await self.pool.close()
            self.pool = None
            self._connected = False
            logger.info("Disconnected from PostgreSQL")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}", exc_info=True)
            # Don't raise - disconnect should always succeed

    async def store(self, data: dict[str, Any]) -> str:
        """
        Store data in PostgreSQL table.

        For active_context table:
            Required fields: session_id, turn_id, content
            Optional fields: metadata, ttl_expires_at

        For working_memory table:
            Required fields: session_id, fact_type, content
            Optional fields: confidence, source_turn_ids, metadata, ttl_expires_at

        Args:
            data: Dictionary with required fields for target table

        Returns:
            String representation of inserted record ID

        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If required fields missing
            StorageQueryError: If insert fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")

        try:
            if self.table == "active_context":
                return await self._store_active_context(data)
            elif self.table == "working_memory":
                return await self._store_working_memory(data)
            else:
                raise StorageDataError(f"Unknown table: {self.table}")

        except StorageDataError:
            raise  # Re-raise validation errors
        except psycopg.Error as e:
            logger.error(f"PostgreSQL insert failed: {e}", exc_info=True)
            raise StorageQueryError(f"Insert failed: {e}") from e

    async def _store_active_context(self, data: dict[str, Any]) -> str:
        """Store record in active_context table"""
        # Validate required fields
        validate_required_fields(data, ["session_id", "turn_id", "content"])

        # Set TTL if not provided (24 hours)
        if "ttl_expires_at" not in data:
            data["ttl_expires_at"] = datetime.now(UTC) + timedelta(hours=24)

        # Prepare metadata
        metadata = json.dumps(data.get("metadata", {}))

        query = sql.SQL("""
            INSERT INTO active_context 
            (session_id, turn_id, content, metadata, created_at, ttl_expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, turn_id) DO NOTHING
            RETURNING id
        """)

        async with self.pool.connection() as conn, conn.cursor() as cur:  # type: ignore
            await cur.execute(
                query,
                (
                    data["session_id"],
                    data["turn_id"],
                    data["content"],
                    metadata,
                    datetime.now(UTC),
                    data["ttl_expires_at"],
                ),
            )
            result = await cur.fetchone()
            # Explicit commit to persist insert; pool connections default to non-autocommit
            await conn.commit()

            if result:
                record_id = str(result[0])
            else:
                # If no result returned, it means a conflict occurred (duplicate).
                # We need to fetch the existing ID to return it.
                logger.warning(
                    f"Duplicate turn detected for session {data['session_id']}, turn {data['turn_id']}. "
                    "Fetching existing ID."
                )
                fetch_query = sql.SQL("""
                    SELECT id FROM active_context 
                    WHERE session_id = %s AND turn_id = %s
                """)
                await cur.execute(fetch_query, (data["session_id"], data["turn_id"]))
                existing_result = await cur.fetchone()
                if existing_result:
                    record_id = str(existing_result[0])
                else:
                    # Should be rare/impossible unless deleted concurrently
                    raise StorageQueryError(
                        "Failed to insert record and failed to retrieve existing duplicate"
                    )

        logger.debug(f"Stored active_context record: {record_id}")
        return record_id

    async def _store_working_memory(self, data: dict[str, Any]) -> str:
        """Store record in working_memory table"""
        # Validate required fields
        validate_required_fields(data, ["session_id", "fact_type", "content"])

        # Set TTL if not provided (7 days)
        if "ttl_expires_at" not in data:
            data["ttl_expires_at"] = datetime.now(UTC) + timedelta(days=7)

        # Prepare metadata and arrays
        metadata = json.dumps(data.get("metadata", {}))
        source_turn_ids = data.get("source_turn_ids", [])

        query = sql.SQL("""
            INSERT INTO working_memory 
            (session_id, fact_type, content, confidence, source_turn_ids, 
             metadata, created_at, updated_at, ttl_expires_at,
             ciar_score, certainty, impact, recency_boost, age_decay)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """)

        async with self.pool.connection() as conn, conn.cursor() as cur:  # type: ignore
            if self.lock_writes:
                lock_query = sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(
                    sql.Identifier(self.table)
                )
                await cur.execute(lock_query)
            await cur.execute(
                query,
                (
                    data["session_id"],
                    data["fact_type"],
                    data["content"],
                    data.get("confidence", 1.0),
                    source_turn_ids,
                    metadata,
                    datetime.now(UTC),
                    datetime.now(UTC),
                    data["ttl_expires_at"],
                    data.get("ciar_score", 0.0),
                    data.get("certainty", 0.7),
                    data.get("impact", 0.5),
                    data.get("recency_boost", 1.0),
                    data.get("age_decay", 1.0),
                ),
            )
            result = await cur.fetchone()
            # Explicit commit to persist insert; pool connections default to non-autocommit
            await conn.commit()
            if result:
                record_id = str(result[0])
            else:
                raise StorageQueryError("Failed to insert record")

        logger.debug(f"Stored working_memory record: {record_id}")
        return record_id

    async def retrieve(self, id: str) -> dict[str, Any] | None:
        """
        Retrieve record by ID.

        Args:
            id: Record ID (integer as string)

        Returns:
            Dictionary with record data, or None if not found

        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If query fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")

        try:
            query = sql.SQL("SELECT * FROM {} WHERE id = %s").format(sql.Identifier(self.table))

            async with self.pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(query, (int(id),))
                row = await cur.fetchone()

                if not row:
                    return None

                    # Get column names
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                else:
                    return None

                    # Convert row to dictionary
                result = dict(zip(columns, row, strict=False))

                # Parse JSON fields
                if result.get("metadata"):
                    result["metadata"] = (
                        json.loads(result["metadata"])
                        if isinstance(result["metadata"], str)
                        else result["metadata"]
                    )

                    # Convert datetime objects to ISO format
                for key, value in result.items():
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()

                return result

        except psycopg.Error as e:
            logger.error(f"PostgreSQL retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Retrieve failed: {e}") from e

    async def search(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Search records with filters.

        Query Parameters:
            - session_id: Filter by session (required for most queries)
            - limit: Maximum results (default: 10)
            - offset: Skip N results (default: 0)
            - include_expired: Include expired records (default: False)
            - sort: Field to sort by (default: 'created_at' or 'turn_id')
            - order: 'asc' or 'desc' (default: 'desc')

        Args:
            query: Dictionary with search parameters

        Returns:
            List of dictionaries containing matching records

        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If search fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")

        try:
            # Build query
            conditions = []
            params = []

            allowed_columns = {
                "active_context": {
                    "id",
                    "session_id",
                    "turn_id",
                    "content",
                    "metadata",
                    "created_at",
                    "ttl_expires_at",
                },
                "working_memory": {
                    "id",
                    "session_id",
                    "fact_type",
                    "content",
                    "confidence",
                    "source_turn_ids",
                    "created_at",
                    "updated_at",
                    "ttl_expires_at",
                    "content_tsv",
                    "ciar_score",
                    "certainty",
                    "impact",
                    "recency_boost",
                    "last_accessed",
                    "access_count",
                    "age_decay",
                },
            }

            # Session filter
            if "session_id" in query:
                conditions.append("session_id = %s")
                params.append(query["session_id"])

            # TTL filter (exclude expired by default)
            if not query.get("include_expired", False):
                conditions.append("(ttl_expires_at IS NULL OR ttl_expires_at > NOW())")

            # Fact type filter (for working_memory)
            if "fact_type" in query:
                conditions.append("fact_type = %s")
                params.append(query["fact_type"])

            # Build WHERE clause
            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Sorting
            order_by = query.get("order_by")
            if order_by:
                order_clause_parts: list[sql.Composable] = []
                for entry in str(order_by).split(","):
                    entry = entry.strip()
                    if not entry:
                        continue
                    tokens = entry.split()
                    column = tokens[0]
                    if self.table in allowed_columns and column not in allowed_columns[self.table]:
                        continue
                    if not column.replace("_", "").isalnum():
                        raise StorageDataError(f"Invalid order_by column: {column}")
                    direction = tokens[1].upper() if len(tokens) > 1 else "DESC"
                    if direction not in ["ASC", "DESC"]:
                        direction = "DESC"
                    order_clause_parts.append(
                        sql.SQL("{} {}").format(
                            sql.Identifier(column),
                            sql.SQL(direction),
                        )
                    )
                if order_clause_parts:
                    order_by_sql = sql.SQL(", ").join(order_clause_parts)
                else:
                    order_by = None

            if not order_by:
                if self.table == "active_context":
                    sort_field = query.get("sort", "turn_id")
                else:
                    sort_field = query.get("sort", "created_at")

                order = query.get("order", "desc").upper()
                if order not in ["ASC", "DESC"]:
                    order = "DESC"
                order_by_sql = sql.SQL("{} {}").format(
                    sql.Identifier(sort_field),
                    sql.SQL(order),
                )

            # Pagination
            limit = query.get("limit", 10)
            offset = query.get("offset", 0)

            # Execute query
            sql_query = sql.SQL("""
                SELECT * FROM {}
                WHERE {}
                ORDER BY {}
                LIMIT %s OFFSET %s
            """).format(
                sql.Identifier(self.table),
                sql.SQL(where_clause),
                order_by_sql,
            )
            params.extend([limit, offset])

            async with self.pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(sql_query, params)
                rows = await cur.fetchall()

                if not rows:
                    return []

                # Get column names
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                else:
                    return []

                # Convert rows to dictionaries
                results = []
                for row in rows:
                    result = dict(zip(columns, row, strict=False))

                    # Parse JSON fields
                    if result.get("metadata"):
                        result["metadata"] = (
                            json.loads(result["metadata"])
                            if isinstance(result["metadata"], str)
                            else result["metadata"]
                        )

                    # Convert datetime to ISO format
                    for key, value in result.items():
                        if isinstance(value, datetime):
                            result[key] = value.isoformat()

                    results.append(result)

                return results

        except psycopg.Error as e:
            logger.error(f"PostgreSQL search failed: {e}", exc_info=True)
            raise StorageQueryError(f"Search failed: {e}") from e

    async def delete(self, id: str) -> bool:
        """
        Delete record by ID.

        Args:
            id: Record ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If delete fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")

        try:
            query = sql.SQL("DELETE FROM {} WHERE id = %s").format(sql.Identifier(self.table))

            async with self.pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(query, (int(id),))
                await conn.commit()
                rowcount = int(cur.rowcount)
                deleted = rowcount > 0

            if deleted:
                logger.debug(f"Deleted record {id} from {self.table}")

            return deleted

        except psycopg.Error as e:
            logger.error(f"PostgreSQL delete failed: {e}", exc_info=True)
            raise StorageQueryError(f"Delete failed: {e}") from e

    async def delete_expired(self) -> int:
        """
        Delete all expired records from table.

        This method should be called periodically as a cleanup job.

        Returns:
            Number of records deleted
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")

        try:
            query = sql.SQL("""
                DELETE FROM {}
                WHERE ttl_expires_at < NOW()
            """).format(sql.Identifier(self.table))

            async with self.pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(query)
                await conn.commit()
                count = int(cur.rowcount)

            if count > 0:
                logger.info(f"Deleted {count} expired records from {self.table}")

            return count

        except psycopg.Error as e:
            logger.error(f"Failed to delete expired records: {e}", exc_info=True)
            raise StorageQueryError(f"Delete expired failed: {e}") from e

    async def count(self, session_id: str | None = None) -> int:
        """
        Count records in table.

        Args:
            session_id: Optional session filter

        Returns:
            Number of records (excluding expired)
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")

        try:
            params: tuple[Any, ...]
            if session_id:
                query = sql.SQL("""
                    SELECT COUNT(*) FROM {}
                    WHERE session_id = %s
                    AND (ttl_expires_at IS NULL OR ttl_expires_at > NOW())
                """).format(sql.Identifier(self.table))
                params = (session_id,)
            else:
                query = sql.SQL("""
                    SELECT COUNT(*) FROM {}
                    WHERE (ttl_expires_at IS NULL OR ttl_expires_at > NOW())
                """).format(sql.Identifier(self.table))
                params = ()

            async with self.pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(query, params)
                result = await cur.fetchone()
                if result:
                    return int(result[0])
                else:
                    return 0

        except psycopg.Error as e:
            logger.error(f"Count query failed: {e}", exc_info=True)
            raise StorageQueryError(f"Count failed: {e}") from e

    async def insert(self, table: str, data: dict[str, Any]) -> str:
        """
        Insert record into specified table (helper method for tiers).

        This is a convenience method used by memory tiers. It temporarily
        switches the target table and calls store().

        Args:
            table: Table name ('active_context' or 'working_memory')
            data: Record data

        Returns:
            Inserted record ID as string

        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If data validation fails
            StorageQueryError: If insert fails
        """
        original_table = self.table
        try:
            self.table = table
            return await self.store(data)
        finally:
            self.table = original_table

    async def execute(self, sql_query: str, *params: Any) -> list[dict[str, Any]]:
        """
        Execute a raw SQL query and return rows as dictionaries.

        Args:
            sql_query: Raw SQL string with parameter placeholders
            *params: Query parameters

        Returns:
            List of result rows as dictionaries

        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If query fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")

        try:
            async with self.pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(sql_query, params)
                rows = await cur.fetchall()

                if not rows or not cur.description:
                    return []

                columns = [desc[0] for desc in cur.description]
                results: list[dict[str, Any]] = []
                for row in rows:
                    result = dict(zip(columns, row, strict=False))
                    if result.get("metadata"):
                        result["metadata"] = (
                            json.loads(result["metadata"])
                            if isinstance(result["metadata"], str)
                            else result["metadata"]
                        )
                    for key, value in result.items():
                        if isinstance(value, datetime):
                            result[key] = value.isoformat()
                    results.append(result)

                return results

        except psycopg.Error as e:
            logger.error(f"PostgreSQL execute failed: {e}", exc_info=True)
            raise StorageQueryError(f"Execute failed: {e}") from e

    async def update(
        self,
        table: str,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        """
        Update records in a specified table.

        Args:
            table: Table name
            filters: Filter conditions for rows to update
            data: Column values to update

        Returns:
            True if any rows were updated

        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If filters or data are empty
            StorageQueryError: If update fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")

        if not filters:
            raise StorageDataError("Update filters cannot be empty")
        if not data:
            raise StorageDataError("Update data cannot be empty")

        try:
            set_clause = sql.SQL(", ").join(
                sql.SQL("{} = %s").format(sql.Identifier(column)) for column in data
            )
            where_clause = sql.SQL(" AND ").join(
                sql.SQL("{} = %s").format(sql.Identifier(column)) for column in filters
            )

            query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
                sql.Identifier(table), set_clause, where_clause
            )

            params = list(data.values()) + list(filters.values())

            async with self.pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()
                return int(cur.rowcount) > 0

        except psycopg.Error as e:
            logger.error(f"PostgreSQL update failed: {e}", exc_info=True)
            raise StorageQueryError(f"Update failed: {e}") from e

    async def delete_by_filters(self, table: str, filters: dict[str, Any]) -> bool:
        """
        Delete records in a specified table using filter conditions.

        Args:
            table: Table name
            filters: Filter conditions for rows to delete

        Returns:
            True if any rows were deleted

        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If filters are empty
            StorageQueryError: If delete fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")

        if not filters:
            raise StorageDataError("Delete filters cannot be empty")

        try:
            where_clause = sql.SQL(" AND ").join(
                sql.SQL("{} = %s").format(sql.Identifier(column)) for column in filters
            )
            query = sql.SQL("DELETE FROM {} WHERE {}").format(sql.Identifier(table), where_clause)
            params = list(filters.values())

            async with self.pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()
                return int(cur.rowcount) > 0

        except psycopg.Error as e:
            logger.error(f"PostgreSQL delete-by-filters failed: {e}", exc_info=True)
            raise StorageQueryError(f"Delete by filters failed: {e}") from e

    async def query(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        order_by: str | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Query records from specified table (helper method for tiers).

        This is a convenience method used by memory tiers. It temporarily
        switches the target table and calls search().

        Args:
            table: Table name ('active_context' or 'working_memory')
            filters: Filter conditions (converted to search parameters)
            limit: Maximum number of results
            **kwargs: Additional search parameters

        Returns:
            List of matching records

        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If query fails
        """
        original_table = self.table
        try:
            self.table = table
            query_params = filters.copy() if filters else {}
            if limit:
                query_params["limit"] = limit
            if order_by:
                query_params["order_by"] = order_by
            query_params.update(kwargs)
            return await self.search(query_params)
        finally:
            self.table = original_table
