# file: memory_system.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone
import uuid
import redis
import json
import asyncio

# Import tier classes
from src.memory.tiers import (
    ActiveContextTier,
    WorkingMemoryTier,
    EpisodicMemoryTier,
    SemanticMemoryTier
)

# Import lifecycle engines
from src.memory.engines.promotion_engine import PromotionEngine
from src.memory.engines.consolidation_engine import ConsolidationEngine
from src.memory.engines.distillation_engine import DistillationEngine

# Import data models
from src.memory.models import Fact, Episode, KnowledgeDocument, ContextBlock, SearchWeights

# Import the facade for the persistent knowledge layer
from knowledge_store_manager import KnowledgeStoreManager

# --- Data Schemas for Operating Memory (Data Contracts) ---

class PersonalMemoryState(BaseModel):
    agent_id: str
    current_task_id: Optional[str] = None
    scratchpad: Dict[str, Any] = Field(default_factory=dict)
    promotion_candidates: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class SharedWorkspaceState(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex}")
    status: Literal["active", "resolved", "cancelled"] = "active"
    shared_data: Dict[str, Any] = Field(default_factory=dict)
    participating_agents: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

# --- Abstract Interface for the COMPLETE Memory System ---

class HybridMemorySystem(ABC):
    """
    Abstract base class defining the contract for the COMPLETE hybrid memory system.
    This is the SINGLE interface agents will use for all memory operations.
    """
    # --- Operating Memory Methods ---
    @abstractmethod
    def get_personal_state(self, agent_id: str) -> PersonalMemoryState:
        pass

    @abstractmethod
    def update_personal_state(self, state: PersonalMemoryState) -> None:
        pass

    @abstractmethod
    def get_shared_state(self, event_id: str) -> SharedWorkspaceState:
        pass

    @abstractmethod
    def update_shared_state(self, state: SharedWorkspaceState) -> None:
        pass
    
    @abstractmethod
    def publish_update(self, event_id: str, update_summary: Dict) -> None:
        pass

    # --- Persistent Knowledge Methods ---
    @abstractmethod
    def query_knowledge(
        self, 
        store_type: Literal["vector", "graph", "search"],
        query_text: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Queries the persistent knowledge layer."""
        pass
    
    # --- Lifecycle Engine Methods ---
    @abstractmethod
    async def run_promotion_cycle(self, session_id: str) -> List[Fact]:
        """Execute L1→L2 promotion cycle with CIAR filtering."""
        pass
    
    @abstractmethod
    async def run_consolidation_cycle(self, session_id: str) -> List[Episode]:
        """Execute L2→L3 consolidation cycle."""
        pass
    
    @abstractmethod
    async def run_distillation_cycle(self, session_id: Optional[str] = None) -> List[KnowledgeDocument]:
        """Execute L3→L4 distillation cycle."""
        pass
    
    # --- Cross-Tier Query Methods ---
    @abstractmethod
    async def query_memory(
        self,
        session_id: str,
        query: str,
        limit: int = 10,
        weights: Optional[SearchWeights] = None
    ) -> List[Dict[str, Any]]:
        """Hybrid semantic search across L2, L3, and L4 tiers."""
        pass
    
    @abstractmethod
    async def get_context_block(
        self,
        session_id: str,
        min_ciar: float = 0.6,
        max_turns: int = 20,
        max_facts: int = 10
    ) -> ContextBlock:
        """Assemble context block for prompt injection."""
        pass

# --- Concrete UNIFIED Implementation ---

class UnifiedMemorySystem(HybridMemorySystem):
    """
    A concrete implementation of the HybridMemorySystem, unifying Operating Memory (Redis)
    and the Persistent Knowledge Layer (via KnowledgeStoreManager).
    
    Integrates all four memory tiers (L1-L4) with lifecycle engines for automated
    information flow and promotion.
    """
    
    def __init__(
        self,
        redis_client: redis.StrictRedis,
        knowledge_manager: KnowledgeStoreManager,
        l1_tier: Optional[ActiveContextTier] = None,
        l2_tier: Optional[WorkingMemoryTier] = None,
        l3_tier: Optional[EpisodicMemoryTier] = None,
        l4_tier: Optional[SemanticMemoryTier] = None,
        promotion_engine: Optional[PromotionEngine] = None,
        consolidation_engine: Optional[ConsolidationEngine] = None,
        distillation_engine: Optional[DistillationEngine] = None
    ):
        """
        Initializes the memory system with clients for all layers.
        
        Args:
            redis_client: Redis client for Operating Memory
            knowledge_manager: Facade for persistent knowledge stores
            l1_tier: Active Context tier (L1) - optional for backward compatibility
            l2_tier: Working Memory tier (L2) - optional for backward compatibility
            l3_tier: Episodic Memory tier (L3) - optional for backward compatibility
            l4_tier: Semantic Memory tier (L4) - optional for backward compatibility
            promotion_engine: L1→L2 promotion engine - optional
            consolidation_engine: L2→L3 consolidation engine - optional
            distillation_engine: L3→L4 distillation engine - optional
        """
        # --- Operating Memory Client ---
        self.redis_client = redis_client
        try:
            if not self.redis_client.ping():
                raise ConnectionError("Could not connect to Redis.")
        except redis.exceptions.ConnectionError as e:
            print(f"Error connecting to Redis: {e}")
            raise

        # --- Persistent Knowledge Layer Client ---
        self.knowledge_manager = knowledge_manager
        
        # --- Memory Tiers ---
        self.l1_tier = l1_tier
        self.l2_tier = l2_tier
        self.l3_tier = l3_tier
        self.l4_tier = l4_tier
        
        # --- Lifecycle Engines ---
        self.promotion_engine = promotion_engine
        self.consolidation_engine = consolidation_engine
        self.distillation_engine = distillation_engine

    # --- Private Key Helpers for Redis ---
    def _get_personal_key(self, agent_id: str) -> str: return f"personal_state:{agent_id}"
    def _get_shared_key(self, event_id: str) -> str: return f"shared_state:{event_id}"
    def _get_channel_key(self, event_id: str) -> str: return f"channel:shared_state:{event_id}"

    # --- Operating Memory Implementation (Delegates to Redis) ---
    def get_personal_state(self, agent_id: str) -> PersonalMemoryState:
        key = self._get_personal_key(agent_id)
        raw_state = self.redis_client.get(key)
        if raw_state is None:
            return PersonalMemoryState(agent_id=agent_id)
        try:
            return PersonalMemoryState.model_validate_json(raw_state)
        except ValidationError as e:
            print(f"Data validation error for agent '{agent_id}': {e}")
            return PersonalMemoryState(agent_id=agent_id)

    def update_personal_state(self, state: PersonalMemoryState) -> None:
        key = self._get_personal_key(state.agent_id)
        state.last_updated = datetime.utcnow()
        self.redis_client.set(key, state.model_dump_json())

    def get_shared_state(self, event_id: str) -> SharedWorkspaceState:
        key = self._get_shared_key(event_id)
        raw_state = self.redis_client.get(key)
        if raw_state is None:
            raise KeyError(f"No shared workspace found for event_id: {event_id}")
        try:
            return SharedWorkspaceState.model_validate_json(raw_state)
        except ValidationError as e:
            raise ValueError(f"Corrupted data for event_id: {event_id}") from e

    def update_shared_state(self, state: SharedWorkspaceState) -> None:
        key = self._get_shared_key(state.event_id)
        state.last_updated = datetime.utcnow()
        self.redis_client.set(key, state.model_dump_json())
        update_summary = {
            "event_id": state.event_id, "status": state.status,
            "last_updated_by": state.participating_agents[-1] if state.participating_agents else "system"
        }
        self.publish_update(state.event_id, update_summary)

    def publish_update(self, event_id: str, update_summary: Dict) -> None:
        channel = self._get_channel_key(event_id)
        self.redis_client.publish(channel, json.dumps(update_summary))

    # --- Persistent Knowledge Implementation (Delegates to KnowledgeStoreManager) ---
    def query_knowledge(
        self, 
        store_type: Literal["vector", "graph", "search"],
        query_text: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Delegates the query to the knowledge store manager."""
        return self.knowledge_manager.query(
            store_type=store_type,
            query_text=query_text,
            top_k=top_k,
            filters=filters
        )
    
    # --- Lifecycle Engine Implementation ---
    
    async def run_promotion_cycle(self, session_id: str) -> List[Fact]:
        """
        Execute L1→L2 promotion cycle with CIAR filtering.
        
        Args:
            session_id: Session to promote turns from
            
        Returns:
            List of Facts promoted to L2
            
        Raises:
            RuntimeError: If promotion engine or required tiers not configured
        """
        if not self.promotion_engine:
            raise RuntimeError("PromotionEngine not configured")
        if not self.l1_tier or not self.l2_tier:
            raise RuntimeError("L1 and L2 tiers required for promotion")
        
        # Run promotion engine
        facts = await self.promotion_engine.promote_session(session_id)
        return facts
    
    async def run_consolidation_cycle(self, session_id: str) -> List[Episode]:
        """
        Execute L2→L3 consolidation cycle.
        
        Args:
            session_id: Session to consolidate facts from
            
        Returns:
            List of Episodes created in L3
            
        Raises:
            RuntimeError: If consolidation engine or required tiers not configured
        """
        if not self.consolidation_engine:
            raise RuntimeError("ConsolidationEngine not configured")
        if not self.l2_tier or not self.l3_tier:
            raise RuntimeError("L2 and L3 tiers required for consolidation")
        
        # Run consolidation engine
        episodes = await self.consolidation_engine.consolidate_session(session_id)
        return episodes
    
    async def run_distillation_cycle(self, session_id: Optional[str] = None) -> List[KnowledgeDocument]:
        """
        Execute L3→L4 distillation cycle.
        
        Args:
            session_id: Optional session filter (None = global distillation)
            
        Returns:
            List of KnowledgeDocuments created in L4
            
        Raises:
            RuntimeError: If distillation engine or required tiers not configured
        """
        if not self.distillation_engine:
            raise RuntimeError("DistillationEngine not configured")
        if not self.l3_tier or not self.l4_tier:
            raise RuntimeError("L3 and L4 tiers required for distillation")
        
        # Run distillation engine
        if session_id:
            knowledge_docs = await self.distillation_engine.distill_session(session_id)
        else:
            knowledge_docs = await self.distillation_engine.distill_global()
        return knowledge_docs
    
    # --- Cross-Tier Query Implementation ---
    
    async def query_memory(
        self,
        session_id: str,
        query: str,
        limit: int = 10,
        weights: Optional[SearchWeights] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid semantic search across L2, L3, and L4 tiers.
        
        Merges results from multiple tiers using configurable weights
        with min-max normalization for comparable scoring.
        
        Args:
            session_id: Session context for search
            query: Search query string
            limit: Maximum results to return
            weights: Search weighting config (default: 0.3/0.5/0.2 for L2/L3/L4)
            
        Returns:
            List of ranked results with unified schema:
            [
                {
                    'content': str,
                    'tier': str (L2/L3/L4),
                    'score': float (0.0-1.0),
                    'metadata': dict
                }
            ]
        """
        if weights is None:
            weights = SearchWeights()  # Use defaults
        
        all_results = []
        
        # L2: Working Memory (Facts)
        if self.l2_tier and weights.l2_weight > 0:
            try:
                l2_facts = await self.l2_tier.retrieve(
                    session_id=session_id,
                    query=query,
                    limit=limit
                )
                # Normalize CIAR scores to 0-1 range
                if l2_facts:
                    l2_scores = [f.ciar_score for f in l2_facts]
                    min_score, max_score = min(l2_scores), max(l2_scores)
                    score_range = max_score - min_score if max_score > min_score else 1.0
                    
                    for fact in l2_facts:
                        normalized_score = (fact.ciar_score - min_score) / score_range if score_range > 0 else 0.5
                        weighted_score = normalized_score * weights.l2_weight
                        all_results.append({
                            'content': fact.content,
                            'tier': 'L2',
                            'score': weighted_score,
                            'metadata': {
                                'fact_id': fact.fact_id,
                                'fact_type': fact.fact_type,
                                'ciar_score': fact.ciar_score,
                                'extracted_at': fact.extracted_at.isoformat()
                            }
                        })
            except Exception as e:
                print(f"L2 query failed: {e}")
        
        # L3: Episodic Memory (Episodes)
        if self.l3_tier and weights.l3_weight > 0:
            try:
                l3_episodes = await self.l3_tier.retrieve(
                    session_id=session_id,
                    query=query,
                    limit=limit
                )
                # Normalize importance scores
                if l3_episodes:
                    l3_scores = [e.importance_score for e in l3_episodes]
                    min_score, max_score = min(l3_scores), max(l3_scores)
                    score_range = max_score - min_score if max_score > min_score else 1.0
                    
                    for episode in l3_episodes:
                        normalized_score = (episode.importance_score - min_score) / score_range if score_range > 0 else 0.5
                        weighted_score = normalized_score * weights.l3_weight
                        all_results.append({
                            'content': episode.summary,
                            'tier': 'L3',
                            'score': weighted_score,
                            'metadata': {
                                'episode_id': episode.episode_id,
                                'fact_count': episode.fact_count,
                                'importance_score': episode.importance_score,
                                'topics': episode.topics,
                                'consolidated_at': episode.consolidated_at.isoformat()
                            }
                        })
            except Exception as e:
                print(f"L3 query failed: {e}")
        
        # L4: Semantic Memory (Knowledge Documents)
        if self.l4_tier and weights.l4_weight > 0:
            try:
                l4_docs = await self.l4_tier.retrieve(
                    query=query,
                    limit=limit
                )
                # Normalize confidence scores
                if l4_docs:
                    l4_scores = [d.confidence_score for d in l4_docs]
                    min_score, max_score = min(l4_scores), max(l4_scores)
                    score_range = max_score - min_score if max_score > min_score else 1.0
                    
                    for doc in l4_docs:
                        normalized_score = (doc.confidence_score - min_score) / score_range if score_range > 0 else 0.5
                        weighted_score = normalized_score * weights.l4_weight
                        all_results.append({
                            'content': doc.content,
                            'tier': 'L4',
                            'score': weighted_score,
                            'metadata': {
                                'knowledge_id': doc.knowledge_id,
                                'title': doc.title,
                                'knowledge_type': doc.knowledge_type,
                                'confidence_score': doc.confidence_score,
                                'tags': doc.tags,
                                'distilled_at': doc.distilled_at.isoformat()
                            }
                        })
            except Exception as e:
                print(f"L4 query failed: {e}")
        
        # Sort by weighted score and limit results
        all_results.sort(key=lambda x: x['score'], reverse=True)
        return all_results[:limit]
    
    async def get_context_block(
        self,
        session_id: str,
        min_ciar: float = 0.6,
        max_turns: int = 20,
        max_facts: int = 10
    ) -> ContextBlock:
        """
        Assemble context block for prompt injection.
        
        Retrieves recent L1 turns and high-CIAR L2 facts, optionally
        including L3 episode summaries and L4 knowledge snippets.
        
        Args:
            session_id: Session to retrieve context for
            min_ciar: Minimum CIAR score for L2 facts
            max_turns: Maximum L1 turns to include
            max_facts: Maximum L2 facts to include
            
        Returns:
            ContextBlock ready for prompt injection
            
        Raises:
            RuntimeError: If required tiers not configured
        """
        context = ContextBlock(
            session_id=session_id,
            min_ciar_threshold=min_ciar
        )
        
        # Retrieve L1 recent turns
        if self.l1_tier:
            try:
                turns = await self.l1_tier.retrieve(
                    session_id=session_id,
                    limit=max_turns
                )
                context.recent_turns = turns
                context.turn_count = len(turns)
            except Exception as e:
                print(f"L1 retrieval failed: {e}")
        
        # Retrieve L2 high-CIAR facts
        if self.l2_tier:
            try:
                facts = await self.l2_tier.retrieve(
                    session_id=session_id,
                    min_ciar_score=min_ciar,
                    limit=max_facts
                )
                context.significant_facts = facts
                context.fact_count = len(facts)
            except Exception as e:
                print(f"L2 retrieval failed: {e}")
        
        # Estimate token count
        context.estimate_token_count()
        
        return context


if __name__ == '__main__':
    # --- Example Usage for the UNIFIED System ---
    
    # This setup requires all database services to be running.
    # We will use mock objects for a simple, self-contained demonstration.
    
    class MockQdrantStore:
        def query_similar(self, **kwargs): return [{"id": 1, "content": "Mock vector search result."}]
    class MockNeo4jStore:
        def query(self, **kwargs): return [{"node": "Mock graph query result."}]
    class MockMeilisearchStore:
        def search(self, **kwargs): return [{"title": "Mock text search result."}]
    
    print("--- Phase 3: Unified Memory System Demo ---")
    
    # 1. Instantiate all backend clients (using mocks for this demo)
    mock_qdrant = MockQdrantStore()
    mock_neo4j = MockNeo4jStore()
    mock_meili = MockMeilisearchStore()
    
    knowledge_manager = KnowledgeStoreManager(
        vector_store=mock_qdrant,
        graph_store=mock_neo4j,
        search_store=mock_meili
    )
    
    # Use an in-memory "fakeredis" for the demo to avoid a real connection
    import fakeredis
    fake_redis_client = fakeredis.FakeStrictRedis(decode_responses=True)
    
    # 2. Instantiate the single, unified memory system
    memory = UnifiedMemorySystem(
        redis_client=fake_redis_client,
        knowledge_manager=knowledge_manager
    )
    print("UnifiedMemorySystem instantiated with mock backends.")

    # 3. Use Operating Memory (same as before)
    agent_id = "port_agent_007"
    print(f"\n--- Testing Operating Memory for agent: {agent_id} ---")
    personal_state = memory.get_personal_state(agent_id)
    personal_state.scratchpad["status"] = "monitoring"
    memory.update_personal_state(personal_state)
    retrieved_state = memory.get_personal_state(agent_id)
    print(f"Retrieved personal state from Redis: {retrieved_state.scratchpad['status']}")
    assert retrieved_state.scratchpad['status'] == 'monitoring'

    # 4. Use Persistent Knowledge Layer THROUGH THE SAME INTERFACE
    print("\n--- Testing Persistent Knowledge Layer ---")
    
    # An agent needs to find similar past events
    vector_results = memory.query_knowledge(
        store_type="vector",
        query_text="Find events about port congestion"
    )
    print(f"Vector search result: {vector_results}")
    assert vector_results[0]['content'] == "Mock vector search result."

    # An agent needs to find a specific relationship
    graph_results = memory.query_knowledge(
        store_type="graph",
        query_text="MATCH (v:Vessel)-[:HAS]->(c:Cargo) RETURN v, c"
    )
    print(f"Graph query result: {graph_results}")
    assert graph_results[0]['node'] == "Mock graph query result."

    # An agent needs to search operational manuals
    search_results = memory.query_knowledge(
        store_type="search",
        query_text="emergency crane protocol"
    )
    print(f"Text search result: {search_results}")
    assert search_results[0]['title'] == "Mock text search result."

    print("\n✅ Demo complete. The UnifiedMemorySystem successfully routes requests to both Operating and Persistent layers.")