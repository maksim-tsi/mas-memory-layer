# file: graph_store_client.py

from typing import Any

from neo4j import GraphDatabase


class Neo4jGraphStore:
    def __init__(self, uri, user, password):
        """Initializes the connection driver for Neo4j."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Closes the database connection driver."""
        self.driver.close()

    def query(
        self, cypher_query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Executes a Cypher query and returns the results.

        Args:
            cypher_query: The Cypher query string to execute.
            params: A dictionary of parameters to bind to the query.

        Returns:
            A list of result dictionaries.
        """
        with self.driver.session() as session:
            result = session.run(cypher_query, params or {})
            return [record.data() for record in result]
