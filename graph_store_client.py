from neo4j import GraphDatabase
from typing import List, Dict, Any

class Neo4jGraphStore:
    def __init__(self, uri, user, password):
        """Initializes the connection driver for Neo4j."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self, cypher_query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Executes a Cypher query and returns the results."""
        with self.driver.session() as session:
            result = session.run(cypher_query, params or {})
            # Process records into a more usable list of dictionaries
            return [record.data() for record in result]