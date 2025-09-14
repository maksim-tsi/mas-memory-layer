from typing import Dict, Any, List, Literal
from .vector_store_client import QdrantVectorStore
from .graph_store_client import Neo4jGraphStore
from .search_store_client import MeilisearchStore
# We can add the relational store later if needed

class KnowledgeStoreManager:
    def __init__(
        self,
        vector_store: QdrantVectorStore,
        graph_store: Neo4jGraphStore,
        search_store: MeilisearchStore
    ):
        """Initializes with instances of all specialized store clients."""
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.search_store = search_store

    def query(
        self, 
        store_type: Literal["vector", "graph", "search"],
        query_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Routes a query to the appropriate knowledge store based on store_type.

        Args:
            store_type: The type of store to query.
            query_params: A dictionary of parameters specific to that store's query method.
                          e.g., for 'vector': {'query_text': '...', 'top_k': 5}
                          e.g., for 'graph': {'cypher_query': 'MATCH ...', 'params': {...}}
                          e.g., for 'search': {'query': '...', 'top_k': 5}
        
        Returns:
            A list of result dictionaries.
        """
        if store_type == "vector":
            return self.vector_store.query_similar(**query_params)
        elif store_type == "graph":
            return self.graph_store.query(**query_params)
        elif store_type == "search":
            return self.search_store.search(**query_params)
        else:
            raise ValueError(f"Unknown store_type: {store_type}")