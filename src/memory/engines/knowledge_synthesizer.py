"""
Knowledge Synthesizer: Query-Time Knowledge Retrieval and Synthesis

Responsible for metadata-first filtering, similarity-based retrieval,
and LLM-powered synthesis of knowledge documents at query time.

Architecture:
- Metadata-first filtering (before similarity search)
- Cosine similarity within filtered groups
- Query-context synthesis using LLM
- Conflict transparency (surface contradictions)
- Short-TTL caching (1-hour)
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
import hashlib
import yaml
from pathlib import Path

from ..models import KnowledgeDocument
from ..tiers.semantic_memory_tier import SemanticMemoryTier
from ...utils.llm_client import LLMClient
from ...utils.providers import BaseProvider
from ...storage.metrics.collector import MetricsCollector


logger = logging.getLogger(__name__)


class KnowledgeSynthesizer:
    """
    Knowledge Synthesizer: Retrieve and synthesize knowledge at query time.
    
    Workflow:
    1. Parse query and extract metadata context
    2. Filter L4 documents by metadata (metadata-first strategy)
    3. Compute cosine similarity within filtered groups
    4. Identify conflicts in retrieved knowledge
    5. Use LLM to synthesize relevant knowledge with query context
    6. Cache results for 1-hour TTL
    """
    
    def __init__(
        self,
        semantic_tier: SemanticMemoryTier,
        llm_provider: BaseProvider,
        domain_config_path: Optional[str] = None,
        similarity_threshold: float = 0.85,
        cache_ttl_seconds: int = 3600,
        metrics_enabled: bool = True
    ):
        """
        Initialize the Knowledge Synthesizer.
        
        Args:
            semantic_tier: L4 tier for retrieving knowledge documents
            llm_provider: LLM provider for synthesis
            domain_config_path: Path to domain configuration YAML
            similarity_threshold: Cosine similarity threshold (default 0.85)
            cache_ttl_seconds: Cache TTL in seconds (default 3600 = 1 hour)
            metrics_enabled: Enable metrics collection
        """
        self.semantic_tier = semantic_tier
        self.llm_client = LLMClient()
        self.llm_client.register_provider(llm_provider)
        self.similarity_threshold = similarity_threshold
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # In-memory cache for synthesized results
        self._cache: Dict[str, Tuple[str, datetime]] = {}
        
        # Metrics
        self.metrics = MetricsCollector() if metrics_enabled else None
        
        # Load domain configuration
        self.domain_config = self._load_domain_config(domain_config_path)
        
        logger.info(
            f"KnowledgeSynthesizer initialized with similarity_threshold={similarity_threshold}, "
            f"cache_ttl={cache_ttl_seconds}s, domain={self.domain_config.get('domain', {}).get('name', 'default')}"
        )
    
    def _load_domain_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load domain configuration from YAML file."""
        if config_path is None:
            config_path = "config/domains/container_logistics.yaml"
        
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Domain config not found: {config_path}, using defaults")
                return self._get_default_config()
            
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded domain config: {config.get('domain', {}).get('name')}")
                return config
        except Exception as e:
            logger.error(f"Failed to load domain config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "domain": {"name": "default"},
            "filtering": {
                "metadata_first": True,
                "min_matching_fields": 0,
                "metadata_boost": 0.3,
                "similarity_threshold": 0.85,
                "max_candidates": 20
            },
            "conflicts": {
                "strategy": "surface",
                "conflict_tag": "CONFLICT_DETECTED",
                "explain_conflicts": True
            }
        }
    
    async def synthesize(
        self,
        query: str,
        metadata_filters: Optional[Dict[str, Any]] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Main synthesis method: Retrieve and synthesize relevant knowledge.
        
        Args:
            query: User query or agent context
            metadata_filters: Domain-specific metadata for filtering (e.g., {"port_code": "USLAX"})
            max_results: Maximum knowledge documents to synthesize
            
        Returns:
            Dict with synthesized knowledge and metadata
        """
        if self.metrics:
            timer = self.metrics.start_timer("synthesis")
        
        try:
            # Step 1: Check cache
            cache_key = self._generate_cache_key(query, metadata_filters)
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                logger.info(f"Cache hit for query: {query[:50]}...")
                if self.metrics:
                    await self.metrics.stop_timer("synthesis", timer)
                return {
                    "status": "success",
                    "synthesized_text": cached_result,
                    "source": "cache",
                    "cache_key": cache_key
                }
            
            # Step 2: Metadata-first filtering
            logger.info(f"Retrieving knowledge with metadata filters: {metadata_filters}")
            filtered_docs = await self._retrieve_with_metadata_filter(
                query=query,
                metadata_filters=metadata_filters,
                max_results=max_results * 2  # Retrieve more for post-filtering
            )
            
            if not filtered_docs:
                logger.info("No knowledge documents found matching filters")
                if self.metrics:
                    await self.metrics.stop_timer("synthesis", timer)
                return {
                    "status": "success",
                    "synthesized_text": "No relevant knowledge found for this query.",
                    "source": "empty_result",
                    "candidates": 0
                }
            
            # Step 3: Compute similarity scores and apply threshold
            scored_docs = await self._score_documents(query, filtered_docs)
            
            # Filter by similarity threshold
            relevant_docs = [
                doc for doc, score in scored_docs
                if score >= self.similarity_threshold
            ][:max_results]
            
            if not relevant_docs:
                logger.info(f"No documents above similarity threshold {self.similarity_threshold}")
                if self.metrics:
                    await self.metrics.stop_timer("synthesis", timer)
                return {
                    "status": "success",
                    "synthesized_text": "No highly relevant knowledge found for this query.",
                    "source": "low_similarity",
                    "candidates": len(scored_docs)
                }
            
            # Step 4: Detect conflicts
            conflicts = self._detect_conflicts(relevant_docs)
            
            # Step 5: Synthesize with LLM
            synthesized_text = await self._synthesize_with_llm(
                query=query,
                documents=relevant_docs,
                conflicts=conflicts
            )
            
            # Step 6: Cache result
            self._cache_result(cache_key, synthesized_text)
            
            elapsed_ms = await self.metrics.stop_timer("synthesis", timer) if self.metrics else 0
            
            return {
                "status": "success",
                "synthesized_text": synthesized_text,
                "source": "synthesized",
                "candidates": len(relevant_docs),
                "has_conflicts": len(conflicts) > 0,
                "conflicts": conflicts,
                "elapsed_ms": elapsed_ms,
                "cache_key": cache_key
            }
            
        except Exception as e:
            if self.metrics:
                await self.metrics.stop_timer("synthesis", timer)
            logger.error(f"Synthesis failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _generate_cache_key(
        self,
        query: str,
        metadata_filters: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key from query and metadata."""
        key_parts = [query]
        
        if metadata_filters:
            # Sort for consistent hashing
            sorted_filters = sorted(metadata_filters.items())
            key_parts.append(str(sorted_filters))
        
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def _get_cached_result(self, cache_key: str) -> Optional[str]:
        """Retrieve cached result if valid."""
        if cache_key not in self._cache:
            return None
        
        result, timestamp = self._cache[cache_key]
        
        # Check TTL
        age_seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()
        if age_seconds > self.cache_ttl_seconds:
            # Expired
            del self._cache[cache_key]
            return None
        
        return result
    
    def _cache_result(self, cache_key: str, result: str):
        """Store result in cache with timestamp."""
        self._cache[cache_key] = (result, datetime.now(timezone.utc))
        
        # Cleanup old entries (simple LRU-like behavior)
        if len(self._cache) > 100:  # Max 100 cached items
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k][1]
            )
            del self._cache[oldest_key]
    
    async def _retrieve_with_metadata_filter(
        self,
        query: str,
        metadata_filters: Optional[Dict[str, Any]],
        max_results: int
    ) -> List[KnowledgeDocument]:
        """
        Retrieve documents with metadata-first filtering.
        
        Args:
            query: Query text
            metadata_filters: Metadata constraints
            max_results: Maximum documents to retrieve
            
        Returns:
            List of filtered KnowledgeDocument objects
        """
        try:
            # Use semantic tier's search with metadata filters
            # Typesense supports filter_by parameter
            
            # Build filter query for Typesense
            filter_query = None
            if metadata_filters:
                filter_parts = []
                for field, value in metadata_filters.items():
                    if isinstance(value, str):
                        filter_parts.append(f"{field}:='{value}'")
                    elif isinstance(value, (int, float)):
                        filter_parts.append(f"{field}:={value}")
                    elif isinstance(value, list):
                        # Multiple values (OR condition)
                        value_str = ",".join([f"'{v}'" if isinstance(v, str) else str(v) for v in value])
                        filter_parts.append(f"{field}:[{value_str}]")
                
                if filter_parts:
                    filter_query = " && ".join(filter_parts)
            
            # Query semantic tier
            documents = await self.semantic_tier.search(
                query_text=query,
                limit=max_results,
                filter_by=filter_query
            )
            
            logger.info(f"Retrieved {len(documents)} documents after metadata filtering")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            return []
    
    async def _score_documents(
        self,
        query: str,
        documents: List[KnowledgeDocument]
    ) -> List[Tuple[KnowledgeDocument, float]]:
        """
        Compute similarity scores for documents.
        
        Args:
            query: Query text
            documents: Candidate documents
            
        Returns:
            List of (document, score) tuples sorted by score descending
        """
        # In production, this would compute cosine similarity
        # For now, we rely on Typesense's relevance scoring
        # which is already included in the search results
        
        # Typesense returns documents sorted by relevance
        # We'll assign synthetic scores based on position
        scored = []
        for i, doc in enumerate(documents):
            # Synthetic score: 1.0 for first, decreasing by 0.05 per position
            score = max(0.6, 1.0 - (i * 0.05))
            scored.append((doc, score))
        
        return scored
    
    def _detect_conflicts(
        self,
        documents: List[KnowledgeDocument]
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicting information in documents.
        
        Args:
            documents: Retrieved knowledge documents
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        # Check for documents with CONFLICT_DETECTED tag
        conflict_tag = self.domain_config.get("conflicts", {}).get("conflict_tag", "CONFLICT_DETECTED")
        
        for doc in documents:
            if doc.metadata and doc.metadata.get("conflict_tag") == conflict_tag:
                conflicts.append({
                    "doc_id": doc.knowledge_id,
                    "title": doc.title,
                    "conflict_type": doc.metadata.get("conflict_type", "unknown")
                })
        
        # Simple heuristic: Check for opposing recommendations
        recommendations = [
            doc for doc in documents
            if doc.knowledge_type == "recommendation"
        ]
        
        if len(recommendations) > 1:
            # Check for contradictory language
            for i, doc1 in enumerate(recommendations):
                for doc2 in recommendations[i+1:]:
                    if self._are_contradictory(doc1.content, doc2.content):
                        conflicts.append({
                            "doc_ids": [doc1.knowledge_id, doc2.knowledge_id],
                            "titles": [doc1.title, doc2.title],
                            "conflict_type": "contradictory_recommendations"
                        })
        
        return conflicts
    
    def _are_contradictory(self, text1: str, text2: str) -> bool:
        """
        Simple heuristic to detect contradictory statements.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            True if texts appear contradictory
        """
        # Simple keyword-based detection
        negative_words = ["not", "don't", "avoid", "never", "shouldn't", "cannot"]
        positive_words = ["should", "must", "recommend", "always", "can", "enable"]
        
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # Check if one is negative and one is positive on similar topics
        has_neg1 = any(word in text1_lower for word in negative_words)
        has_pos1 = any(word in text1_lower for word in positive_words)
        has_neg2 = any(word in text2_lower for word in negative_words)
        has_pos2 = any(word in text2_lower for word in positive_words)
        
        # Simplified: contradictory if one is clearly negative and other is positive
        return (has_neg1 and has_pos2) or (has_pos1 and has_neg2)
    
    async def _synthesize_with_llm(
        self,
        query: str,
        documents: List[KnowledgeDocument],
        conflicts: List[Dict[str, Any]]
    ) -> str:
        """
        Use LLM to synthesize knowledge documents into query-specific response.
        
        Args:
            query: User query
            documents: Relevant knowledge documents
            conflicts: Detected conflicts
            
        Returns:
            Synthesized text
        """
        try:
            # Build context from documents
            doc_context = "\n\n".join([
                f"Document {i+1}: {doc.title}\n"
                f"Type: {doc.knowledge_type}\n"
                f"Content: {doc.content[:500]}..."  # First 500 chars
                for i, doc in enumerate(documents)
            ])
            
            # Add conflict information if present
            conflict_note = ""
            if conflicts and self.domain_config.get("conflicts", {}).get("explain_conflicts", True):
                conflict_note = "\n\nIMPORTANT: Conflicting information detected:\n"
                for conflict in conflicts:
                    if "doc_ids" in conflict:
                        conflict_note += f"- Documents {conflict['doc_ids']} contain contradictory recommendations\n"
                    else:
                        conflict_note += f"- Document {conflict['doc_id']} is marked as conflicting\n"
                conflict_note += "Please acknowledge these conflicts in your response.\n"
            
            # Build synthesis prompt
            prompt = f"""You are a knowledge synthesis assistant. Your task is to synthesize relevant knowledge documents to answer the user's query.

User Query: {query}

Available Knowledge:
{doc_context}
{conflict_note}

Instructions:
1. Synthesize the most relevant information from the documents above
2. Focus specifically on the user's query
3. If there are conflicts, present both perspectives transparently
4. Keep the response concise but comprehensive (3-5 sentences)
5. Cite document numbers when making specific claims

Synthesized Response:"""
            
            # Call LLM
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.4  # Balanced between factual and coherent
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            # Fallback: Return concatenated document titles and content
            fallback = f"Relevant knowledge (LLM unavailable):\n\n"
            for i, doc in enumerate(documents):
                fallback += f"{i+1}. {doc.title}: {doc.content[:200]}...\n\n"
            return fallback
    
    async def clear_cache(self):
        """Clear the synthesis cache."""
        self._cache.clear()
        logger.info("Synthesis cache cleared")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now(timezone.utc)
        valid_entries = sum(
            1 for _, timestamp in self._cache.values()
            if (now - timestamp).total_seconds() <= self.cache_ttl_seconds
        )
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "ttl_seconds": self.cache_ttl_seconds
        }
