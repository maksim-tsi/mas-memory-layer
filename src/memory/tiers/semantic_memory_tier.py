"""
L4: Semantic Memory Tier - Distilled Knowledge Store

Stores generalized knowledge documents distilled from L3 episodes.
Provides full-text search, faceted filtering, and provenance tracking.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.memory.tiers.base_tier import BaseTier
from src.storage.typesense_adapter import TypesenseAdapter
from src.storage.metrics.collector import MetricsCollector
from src.storage.metrics.timer import OperationTimer
from src.memory.models import KnowledgeDocument


class SemanticMemoryTier(BaseTier):
    """
    L4: Semantic Memory - Distilled Knowledge Repository
    
    Stores permanent, generalized knowledge mined from L3 episodes.
    Supports full-text search, faceted filtering, and provenance tracking.
    """
    
    COLLECTION_NAME = "knowledge_base"
    
    def __init__(
        self,
        typesense_adapter: TypesenseAdapter,
        metrics_collector: Optional[MetricsCollector] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        storage_adapters = {'typesense': typesense_adapter}
        super().__init__(storage_adapters, metrics_collector, config)
        
        self.typesense = typesense_adapter
        self.collection_name = config.get('collection_name', self.COLLECTION_NAME) if config else self.COLLECTION_NAME
    
    async def initialize(self) -> None:
        """Initialize Typesense collection."""
        # Call parent initialize to connect adapter
        await super().initialize()
    
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store a knowledge document in L4.
        
        Args:
            data: KnowledgeDocument object or dict
            
        Returns:
            Knowledge identifier
        """
        async with OperationTimer(self.metrics, 'l4_store'):
            # Convert to KnowledgeDocument for validation
            if isinstance(data, dict):
                knowledge = KnowledgeDocument(**data)
            else:
                knowledge = data
            
            # Store in Typesense
            await self.typesense.index_document(
                collection_name=self.collection_name,
                document=knowledge.to_typesense_document()
            )
            
            return knowledge.knowledge_id
    
    async def retrieve(self, knowledge_id: str) -> Optional[KnowledgeDocument]:
        """
        Retrieve knowledge document by ID.
        
        Args:
            knowledge_id: Knowledge identifier
            
        Returns:
            KnowledgeDocument or None
        """
        async with OperationTimer(self.metrics, 'l4_retrieve'):
            result = await self.typesense.get_document(
                collection_name=self.collection_name,
                document_id=knowledge_id
            )
            
            if not result:
                return None
            
            # Convert back to KnowledgeDocument
            knowledge = KnowledgeDocument(
                knowledge_id=result['id'],
                title=result['title'],
                content=result['content'],
                knowledge_type=result['knowledge_type'],
                confidence_score=result['confidence_score'],
                source_episode_ids=result.get('source_episode_ids', []),
                episode_count=result['episode_count'],
                provenance_links=result.get('provenance_links', []),
                category=result.get('category'),
                tags=result.get('tags', []),
                domain=result.get('domain'),
                distilled_at=datetime.fromtimestamp(result['distilled_at'], tz=timezone.utc),
                access_count=result['access_count'],
                usefulness_score=result['usefulness_score'],
                validation_count=result['validation_count']
            )
            
            # Update access tracking
            await self._update_access(knowledge)
            
            return knowledge
    
    async def search(
        self,
        query_text: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[KnowledgeDocument]:
        """
        Full-text search for knowledge documents.
        
        Args:
            query_text: Search query
            filters: Optional filters (knowledge_type, category, tags, min_confidence)
            limit: Max results
            
        Returns:
            List of matching knowledge documents
        """
        async with OperationTimer(self.metrics, 'l4_search'):
            # Build filter string
            filter_by = []
            if filters:
                if 'knowledge_type' in filters:
                    filter_by.append(f"knowledge_type:={filters['knowledge_type']}")
                if 'category' in filters:
                    filter_by.append(f"category:={filters['category']}")
                if 'min_confidence' in filters:
                    filter_by.append(f"confidence_score:>={filters['min_confidence']}")
                if 'tags' in filters:
                    tag_filter = ' || '.join([f"tags:={tag}" for tag in filters['tags']])
                    filter_by.append(f"({tag_filter})")
            
            # Execute search
            results = await self.typesense.search(
                collection_name=self.collection_name,
                query=query_text,
                query_by='title,content',
                filter_by=' && '.join(filter_by) if filter_by else None,
                limit=limit,
                sort_by='usefulness_score:desc'
            )
            
            # Convert to KnowledgeDocument objects
            documents = []
            for hit in results.get('hits', []):
                doc = hit['document']
                knowledge = KnowledgeDocument(
                    knowledge_id=doc['id'],
                    title=doc['title'],
                    content=doc['content'],
                    knowledge_type=doc['knowledge_type'],
                    confidence_score=doc['confidence_score'],
                    source_episode_ids=doc.get('source_episode_ids', []),
                    episode_count=doc['episode_count'],
                    provenance_links=doc.get('provenance_links', []),
                    category=doc.get('category'),
                    tags=doc.get('tags', []),
                    domain=doc.get('domain'),
                    distilled_at=datetime.fromtimestamp(doc['distilled_at'], tz=timezone.utc),
                    access_count=doc['access_count'],
                    usefulness_score=doc['usefulness_score'],
                    validation_count=doc['validation_count']
                )
                # Attach search score
                knowledge.metadata['search_score'] = hit.get('text_match', 0)
                documents.append(knowledge)
            
            return documents
    
    async def query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        **kwargs
    ) -> List[KnowledgeDocument]:
        """
        Query knowledge documents with filters (without text search).
        
        Args:
            filters: Query filters
            limit: Max results
            
        Returns:
            List of knowledge documents
        """
        # Use search with wildcard query
        return await self.search(
            query_text='*',
            filters=filters,
            limit=limit
        )
    
    async def update_usefulness(
        self,
        knowledge_id: str,
        usefulness_score: float
    ) -> bool:
        """
        Update usefulness score based on feedback.
        
        Args:
            knowledge_id: Knowledge to update
            usefulness_score: New score (0.0-1.0)
            
        Returns:
            True if updated
        """
        # Retrieve current document
        doc = await self.retrieve(knowledge_id)
        if not doc:
            return False
        
        # Update score
        doc.usefulness_score = usefulness_score
        doc.validation_count += 1
        doc.last_validated = datetime.now(timezone.utc)
        
        # Re-index
        await self.typesense.update_document(
            collection_name=self.collection_name,
            document_id=knowledge_id,
            document=doc.to_typesense_document()
        )
        
        return True
    
    async def delete(self, knowledge_id: str) -> bool:
        """
        Delete knowledge document from L4.
        
        Args:
            knowledge_id: Knowledge identifier
            
        Returns:
            True if deleted
        """
        async with OperationTimer(self.metrics, 'l4_delete'):
            await self.typesense.delete_document(
                collection_name=self.collection_name,
                document_id=knowledge_id
            )
            
            return True
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Statistics dictionary
        """
        # Get all documents (limited sample)
        sample = await self.query(limit=1000)
        
        if not sample:
            return {
                'total_documents': 0,
                'avg_confidence': 0.0,
                'avg_usefulness': 0.0
            }
        
        from collections import Counter
        types = Counter([d.knowledge_type for d in sample])
        categories = Counter([d.category for d in sample if d.category])
        
        return {
            'total_documents': len(sample),
            'avg_confidence': sum(d.confidence_score for d in sample) / len(sample),
            'avg_usefulness': sum(d.usefulness_score for d in sample) / len(sample),
            'avg_episode_count': sum(d.episode_count for d in sample) / len(sample),
            'knowledge_types': dict(types),
            'categories': dict(categories),
            'most_useful': max(sample, key=lambda d: d.usefulness_score).knowledge_id,
            'most_accessed': max(sample, key=lambda d: d.access_count).knowledge_id
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of Typesense."""
        typesense_health = await self.typesense.health_check()
        
        # Get statistics
        stats = await self.get_statistics()
        
        return {
            'tier': 'L4_semantic_memory',
            'status': typesense_health['status'],
            'storage': {'typesense': typesense_health},
            'statistics': stats
        }
    
    async def _update_access(self, knowledge: KnowledgeDocument) -> None:
        """Update access tracking for a knowledge document."""
        knowledge.access_count += 1
        knowledge.last_accessed = datetime.now(timezone.utc)
        
        await self.typesense.update_document(
            collection_name=self.collection_name,
            document_id=knowledge.knowledge_id,
            document=knowledge.to_typesense_document()
        )
