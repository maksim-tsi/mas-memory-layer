from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

class QdrantVectorStore:
    def __init__(self, host: str, port: int, collection_name: str):
        """Initializes the connection to the Qdrant database."""
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        # In a real system, the embedding model should also be configurable
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2") 
        # Ensure the collection exists
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
        """
        self.client.upload_points(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=doc["id"],
                    vector=self.encoder.encode(doc["content"]).tolist(),
                    payload=doc,
                )
                for doc in documents
            ],
        )

    def query_similar(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Finds the most similar documents to a query string."""
        query_vector = self.encoder.encode(query_text).tolist()
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
        )
        return [hit.payload for hit in hits]