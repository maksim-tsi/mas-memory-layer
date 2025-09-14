import meilisearch
from typing import List, Dict, Any

class MeilisearchStore:
    def __init__(self, host_url: str, api_key: str, index_name: str):
        """Initializes the connection to Meilisearch."""
        self.client = meilisearch.Client(host_url, api_key)
        self.index_name = index_name
        self.index = self.client.index(index_name)

    def add_documents(self, documents: List[Dict[str, Any]], primary_key: str = 'id'):
        """
        Adds or updates documents in the Meilisearch index.
        Documents should be a list of dictionaries.
        """
        self.index.add_documents(documents, primary_key=primary_key)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs a full-text search."""
        search_results = self.index.search(query, {'limit': top_k})
        return search_results['hits']