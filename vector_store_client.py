# file: vector_store_client.py

import uuid
from typing import List, Dict, Any, Optional, Union
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

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
            host: Qdrant server host.
            port: Qdrant server port.
            collection_name: Name of the collection to use.
            model_name: Name of the sentence transformer model for embeddings.
        """
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.encoder = SentenceTransformer(model_name)
        self._create_collection_if_not_exists()
    
    def _create_collection_if_not_exists(self):
        """Creates the collection if it doesn't exist already."""
        try:
            self.client.get_collection(collection_name=self.collection_name)
        except Exception: # A more specific exception can be used depending on the client version
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.encoder.get_sentence_embedding_dimension(),
                    distance=models.Distance.COSINE
                ),
            )

    def recreate_collection(self):
        """Drops and recreates the collection."""
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.encoder.get_sentence_embedding_dimension(),
                distance=models.Distance.COSINE
            ),
        )
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> List[Union[str, int]]:
        """
        Embeds and stores a list of documents in Qdrant.
        Each document is a dict with 'content' and an optional 'id'.
        
        Args:
            documents: List of documents to add.
            
        Returns:
            A list of IDs for the added documents.
        """
        points = []
        doc_ids = []
        for doc in documents:
            doc_id = doc.get("id", str(uuid.uuid4()))
            point_id = doc_id if isinstance(doc_id, (int, str)) else str(doc_id)
            doc_ids.append(point_id)
            
            vector = self.encoder.encode(doc["content"]).tolist()
            
            points.append(
                models.PointStruct(id=point_id, vector=vector, payload=doc)
            )
        
        self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
        return doc_ids
    
    def query_similar(
        self, 
        query_text: str, 
        top_k: int = 5,
        filters: Optional[models.Filter] = None
    ) -> List[Dict[str, Any]]:
        """
        Finds the most similar documents to a query string.
        
        Args:
            query_text: The text to find similar documents for.
            top_k: Number of results to return.
            filters: Optional Qdrant filter object.
            
        Returns:
            List of document payloads sorted by similarity.
        """
        query_vector = self.encoder.encode(query_text).tolist()
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=filters,
            limit=top_k,
        )
        return [hit.payload for hit in hits]
    
    def delete_documents(self, ids: List[Union[str, int]]):
        """Deletes documents by their IDs."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=ids),
        )