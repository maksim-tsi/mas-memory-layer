import meilisearch
from typing import List, Dict, Any, Optional

class MeilisearchStore:
    def __init__(self, host_url: str, api_key: str, index_name: str):
        """Initializes the connection to Meilisearch.
        
        Args:
            host_url: The URL where Meilisearch server is running
            api_key: The API key for authentication
            index_name: The name of the index to use
        """
        self.client = meilisearch.Client(host_url, api_key)
        self.index_name = index_name
        self.index = self.client.index(index_name)
        
        # Ensure the index exists
        try:
            self.client.get_index(index_name)
        except meilisearch.errors.MeiliSearchApiError:
            self.client.create_index(index_name)
            self.index = self.client.index(index_name)

    def configure_index(self, filterable_attributes: Optional[List[str]] = None, 
                        sortable_attributes: Optional[List[str]] = None,
                        searchable_attributes: Optional[List[str]] = None):
        """Configure index settings for better search experience.
        
        Args:
            filterable_attributes: Attributes that can be used for filtering
            sortable_attributes: Attributes that can be used for sorting
            searchable_attributes: Attributes that should be searchable
        """
        settings = {}
        
        if filterable_attributes:
            settings['filterableAttributes'] = filterable_attributes
        
        if sortable_attributes:
            settings['sortableAttributes'] = sortable_attributes
            
        if searchable_attributes:
            settings['searchableAttributes'] = searchable_attributes
            
        if settings:
            self.index.update_settings(settings)

    def add_documents(self, documents: List[Dict[str, Any]], primary_key: str = 'id'):
        """
        Adds or updates documents in the Meilisearch index.
        Documents should be a list of dictionaries.
        
        Args:
            documents: List of document dictionaries to add to the index
            primary_key: The field to use as the primary key for documents
        
        Returns:
            The task ID that can be used to check the status of the operation
        """
        task = self.index.add_documents(documents, primary_key=primary_key)
        return task

    def search(self, query: str, top_k: int = 5, filters: str = None) -> List[Dict[str, Any]]:
        """Performs a full-text search.
        
        Args:
            query: The search query string
            top_k: Maximum number of results to return
            filters: Optional filter expression (e.g., "category = 'supply' AND priority > 2")
            
        Returns:
            A list of matching documents
        """
        search_params = {'limit': top_k}
        if filters:
            search_params['filter'] = filters
            
        search_results = self.index.search(query, search_params)
        return search_results['hits']
    
    def delete_documents(self, document_ids: List[str]) -> dict:
        """Delete documents from the index by their IDs.
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            Task information dictionary
        """
        task = self.index.delete_documents(document_ids)
        return task
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Retrieve a single document by its ID.
        
        Args:
            document_id: ID of the document to retrieve
            
        Returns:
            The document dictionary
        """
        return self.index.get_document(document_id)