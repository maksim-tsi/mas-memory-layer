from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Union
import numpy as np
import uuid

class QdrantVectorStore:
    def __init__(
        self, 
        host: str, 
        port: int, 
        collection_name: str,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        Initializes the connection to the Qdrant database.
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Name of the collection to use
            model_name: Name of the sentence transformer model to use for embeddings
        """
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.encoder = SentenceTransformer(model_name)
        
        # Ensure the collection exists
        self._create_collection_if_not_exists()
    
    def _create_collection_if_not_exists(self):
        """Creates the collection if it doesn't exist already"""
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.encoder.get_sentence_embedding_dimension(),
                    distance=models.Distance.COSINE
                ),
            )

    def recreate_collection(self):
        """Drops and recreates the collection"""
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.encoder.get_sentence_embedding_dimension(),
                distance=models.Distance.COSINE
            ),
        )
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Embeds and stores a list of documents in Qdrant.
        Each document is a dict with 'id' and 'content' keys.
        
        Args:
            documents: List of documents to add
        """
        points = []
        for doc in documents:
            # Generate ID if not provided
            doc_id = doc.get("id", str(uuid.uuid4()))
            
            # Ensure ID is the right type
            if isinstance(doc_id, int) or isinstance(doc_id, str):
                point_id = doc_id
            else:
                point_id = str(doc_id)
                
            vector = self.encoder.encode(doc["content"]).tolist()
            
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=doc,
                )
            )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        
        return [point.id for point in points]
    
    def add_document(self, document: Dict[str, Any]):
        """
        Embeds and stores a single document in Qdrant.
        
        Args:
            document: Document to add with 'content' key
            
        Returns:
            ID of the added document
        """
        return self.add_documents([document])[0]

    def query_similar(
        self, 
        query_text: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Finds the most similar documents to a query string.
        
        Args:
            query_text: The text to find similar documents for
            top_k: Number of results to return
            filters: Optional Qdrant filter conditions
            
        Returns:
            List of document payloads sorted by similarity
        """
        query_vector = self.encoder.encode(query_text).tolist()
        search_params = {
            "collection_name": self.collection_name,
            "query_vector": query_vector,
            "limit": top_k,
        }
        
        if filters:
            search_params["query_filter"] = models.Filter(**filters)
            
        hits = self.client.search(**search_params)
        return [hit.payload for hit in hits]
    
    def query_by_vector(
        self, 
        query_vector: Union[List[float], np.ndarray], 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Finds the most similar documents to a query vector.
        
        Args:
            query_vector: The embedding vector to search with
            top_k: Number of results to return
            filters: Optional Qdrant filter conditions
            
        Returns:
            List of document payloads sorted by similarity
        """
        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.tolist()
            
        search_params = {
            "collection_name": self.collection_name,
            "query_vector": query_vector,
            "limit": top_k,
        }
        
        if filters:
            search_params["query_filter"] = models.Filter(**filters)
            
        hits = self.client.search(**search_params)
        return [hit.payload for hit in hits]
    
    def delete_documents(self, ids: List[Union[str, int]]):
        """
        Deletes documents by their IDs
        
        Args:
            ids: List of document IDs to delete
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=ids,
            ),
        )