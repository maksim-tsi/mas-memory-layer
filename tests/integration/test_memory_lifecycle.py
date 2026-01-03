"""
Integration Tests for Full Memory Lifecycle (L1→L2→L3→L4).

Tests the complete information flow through all four tiers using the
live research cluster with namespace isolation.

Test Scope:
- L1: Store raw conversation turns in Redis
- L2: Promote significant facts to PostgreSQL (CIAR filtering)
- L3: Consolidate facts into episodes in Qdrant + Neo4j
- L4: Distill episodes into knowledge patterns in Typesense

Each test uses unique session_id for namespace isolation and surgical cleanup.
"""

import pytest
import asyncio
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from src.memory.tiers.active_context_tier import ActiveContextTier
from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.tiers.episodic_memory_tier import EpisodicMemoryTier
from src.memory.tiers.semantic_memory_tier import SemanticMemoryTier
from src.memory.engines.promotion_engine import PromotionEngine
from src.memory.engines.consolidation_engine import ConsolidationEngine
from src.memory.engines.distillation_engine import DistillationEngine
from src.memory.engines.topic_segmenter import TopicSegmenter
from src.memory.engines.fact_extractor import FactExtractor
from src.memory.ciar_scorer import CIARScorer


pytestmark = pytest.mark.integration


class TestMemoryLifecycleFlow:
    """Test full L1→L2→L3→L4 lifecycle flow."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_l1_to_l2_promotion_with_ciar_filtering(
        self,
        test_session_id,
        test_user_id,
        redis_adapter,
        postgres_adapter,
        real_llm_client,
        test_settings,
        report_collector,
        full_cleanup
    ):
        """Test L1→L2 promotion with CIAR score filtering using real LLM.
        
        Workflow:
        1. Store 12 raw turns in L1 (Redis) with session_id/user_id
        2. Run PromotionEngine with real Groq/Gemini LLM
        3. Verify facts promoted to L2 have CIAR ≥ 0.6
        4. Record promotion latency + LLM provider used
        """
        llm_client, provider_name = real_llm_client
        latencies = {}
        
        # 1. Initialize tiers
        l1_tier = ActiveContextTier(redis_adapter, postgres_adapter)
        l2_tier = WorkingMemoryTier(postgres_adapter)
        
        # 2. Store test turns in L1 (above batch_min_turns threshold)
        turns = create_test_turns(test_session_id, count=12)
        start_store = time.perf_counter()
        for turn in turns:
            turn['user_id'] = test_user_id
            await l1_tier.store(turn)
        latencies['l1_store_ms'] = (time.perf_counter() - start_store) * 1000
        
        # 3. Create promotion engine with real LLM
        # Determine correct model name based on active provider
        if provider_name == 'groq':
            model_name = test_settings.llm_providers['fallback']['model']  # openai/gpt-oss-120b (now fallback)
        elif provider_name == 'google-pro':
            model_name = test_settings.llm_providers['fallback_reasoning']['model']  # gemini-3-pro-preview
        else:  # google/gemini (flash) - now primary
            model_name = test_settings.llm_providers['primary']['model']  # gemini-3-flash-preview
        
        topic_segmenter = TopicSegmenter(llm_client, model_name=model_name)
        fact_extractor = FactExtractor(llm_client, model_name=model_name)
        ciar_scorer = CIARScorer()
        
        promotion_engine = PromotionEngine(
            l1_tier=l1_tier,
            l2_tier=l2_tier,
            topic_segmenter=topic_segmenter,
            fact_extractor=fact_extractor,
            ciar_scorer=ciar_scorer,
            config={'promotion_threshold': 0.6, 'batch_min_turns': 10}
        )
        
        # Apply throttle before LLM call
        await asyncio.sleep(test_settings.llm_throttle_seconds)
        
        # 4. Execute promotion cycle
        start_promotion = time.perf_counter()
        stats = await promotion_engine.process_session(test_session_id)
        latencies['promotion_ms'] = (time.perf_counter() - start_promotion) * 1000
        
        # Apply throttle after LLM call
        await asyncio.sleep(test_settings.llm_throttle_seconds)
        
        # 5. Verify facts promoted to L2
        promoted_facts = await l2_tier.query_by_session(test_session_id)
        
        # Assert at least some facts were promoted
        assert len(promoted_facts) > 0, f"No facts promoted from {stats['turns_retrieved']} turns"
        assert stats['facts_promoted'] > 0, "Promotion engine reported 0 facts promoted"
        
        # Verify CIAR threshold filtering
        for fact in promoted_facts:
            ciar_score = fact.get('ciar_score', 0)
            assert ciar_score >= 0.6, f"Fact with CIAR {ciar_score} below threshold 0.6"
        
        # Record results
        report_collector.add_result(
            test_name='test_l1_to_l2_promotion_with_ciar_filtering',
            latencies=latencies,
            provider=provider_name,
            passed=True,
            metadata={
                'turns_stored': len(turns),
                'facts_promoted': len(promoted_facts),
                'promotion_stats': stats
            }
        )
        
        print(f"✅ Promoted {len(promoted_facts)} facts from {len(turns)} turns using {provider_name}")
        print(f"📊 Latencies: L1 store={latencies['l1_store_ms']:.2f}ms, promotion={latencies['promotion_ms']:.2f}ms")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_l2_to_l3_consolidation_with_episode_clustering(
        self,
        test_session_id,
        test_user_id,
        postgres_adapter,
        neo4j_adapter,
        qdrant_adapter,
        real_llm_client,
        test_settings,
        report_collector,
        full_cleanup
    ):
        """Test L2→L3 consolidation with dual-index verification.
        
        Workflow:
        1. Store 50+ facts in L2 with session_id/user_id
        2. Run ConsolidationEngine
        3. Query both Qdrant (vector) and Neo4j (graph) for episodes
        4. Verify same episode_id exists in both stores
        5. Verify metadata consistency across stores
        """
        llm_client, provider_name = real_llm_client
        latencies = {}
        
        # 1. Initialize tiers
        l2_tier = WorkingMemoryTier(postgres_adapter)
        l3_tier = EpisodicMemoryTier(qdrant_adapter, neo4j_adapter)
        
        # 2. Store test facts in L2 (above consolidation trigger)
        facts = create_test_facts(test_session_id, count=50)
        start_store = time.perf_counter()
        for fact in facts:
            fact['user_id'] = test_user_id
            await l2_tier.store(fact)
        latencies['l2_store_ms'] = (time.perf_counter() - start_store) * 1000
        
        # 3. Create consolidation engine
        consolidation_engine = ConsolidationEngine(
            l2_tier=l2_tier,
            l3_tier=l3_tier,
            llm_provider=llm_client,
            config={'consolidation_threshold': 50}
        )
        
        # Apply throttle
        await asyncio.sleep(test_settings.llm_throttle_seconds)
        
        # STEP 0: Get point count BEFORE consolidation
        points_before = 0
        if hasattr(qdrant_adapter, 'client') and qdrant_adapter.client:
            try:
                info_before = await qdrant_adapter.client.get_collection('episodes')
                points_before = info_before.points_count
                print(f"DEBUG STEP0: Points BEFORE consolidation = {points_before}")
            except Exception as e:
                print(f"DEBUG STEP0: Failed: {e}")
        
        # 4. Execute consolidation
        start_consolidation = time.perf_counter()
        stats = await consolidation_engine.process_session(test_session_id)
        latencies['consolidation_ms'] = (time.perf_counter() - start_consolidation) * 1000
        
        await asyncio.sleep(test_settings.llm_throttle_seconds)

        print(f"DEBUG: Consolidation stats={stats}")
        assert stats.get('episodes_created', 0) > 0, f"Consolidation produced no episodes: {stats}"
        
        # 5. Verify dual indexing
        # STEP 1: Check adapter identity
        test_qdrant_id = id(qdrant_adapter)
        l3_qdrant_id = id(l3_tier.qdrant)
        test_qdrant_url = getattr(qdrant_adapter, 'url', getattr(qdrant_adapter, '_url', 'UNKNOWN'))
        l3_qdrant_url = getattr(l3_tier.qdrant, 'url', getattr(l3_tier.qdrant, '_url', 'UNKNOWN'))
        print(f"DEBUG STEP1: test_qdrant_adapter id={test_qdrant_id}, url={test_qdrant_url}")
        print(f"DEBUG STEP1: l3_tier.qdrant id={l3_qdrant_id}, url={l3_qdrant_url}")
        print(f"DEBUG STEP1: SAME_ADAPTER={test_qdrant_id == l3_qdrant_id}")
        
        # STEP 2: Get collection info via scroll (no vector needed)
        if hasattr(qdrant_adapter, 'client') and qdrant_adapter.client:
            try:
                collection_info = await qdrant_adapter.client.get_collection('episodes')
                print(f"DEBUG STEP2: Collection 'episodes' points_count={collection_info.points_count} (was {points_before} before)")
                print(f"DEBUG STEP2: Points ADDED = {collection_info.points_count - points_before}")
            except Exception as e:
                print(f"DEBUG STEP2: Failed to get collection info: {e}")
        
        # STEP 4: Use scroll to list ALL points (no vector similarity)
        if hasattr(qdrant_adapter, 'client') and qdrant_adapter.client:
            try:
                scroll_result = await qdrant_adapter.client.scroll(
                    collection_name='episodes',
                    limit=20,
                    with_payload=True
                )
                points, next_offset = scroll_result
                print(f"DEBUG STEP4: Scroll found {len(points)} points")
                found_our_session = False
                for i, p in enumerate(points):
                    p_session = p.payload.get('session_id', 'NONE') if p.payload else 'NO_PAYLOAD'
                    marker = " <-- OUR SESSION" if p_session == test_session_id else ""
                    if p_session == test_session_id:
                        found_our_session = True
                    print(f"DEBUG STEP4: Point[{i}] id={p.id}, session_id={p_session}{marker}")
                print(f"DEBUG STEP4: Found our session ({test_session_id}): {found_our_session}")
            except Exception as e:
                print(f"DEBUG STEP4: Scroll failed: {e}")
        
        # Now do the original search tests
        # First, check if ANY data exists in Qdrant (no filter)
        all_results = await qdrant_adapter.search({
            'vector': [0.1] * l3_tier.vector_size,
            'limit': 10,
            'collection_name': l3_tier.collection_name,
        })
        print(f"DEBUG: Qdrant ALL results (no filter)={len(all_results)}")
        if all_results:
            for i, r in enumerate(all_results[:3]):
                print(f"DEBUG: Result[{i}] session_id={r.get('session_id')}, score={r.get('score')}")
        
        # Query Qdrant with session_id filter using SCROLL (no vector similarity needed)
        # This is the correct approach - scroll retrieves by filter, search requires vector similarity
        print(f"DEBUG: Scrolling Qdrant - session={test_session_id}, collection={l3_tier.collection_name}")
        qdrant_results = await qdrant_adapter.scroll(
            filter_dict={'session_id': test_session_id},
            limit=10,
            collection_name=l3_tier.collection_name,
        )
        print(f"DEBUG: Qdrant scroll results={len(qdrant_results)}")
        if qdrant_results:
            for i, r in enumerate(qdrant_results[:3]):
                print(f"DEBUG: ScrollResult[{i}] session_id={r.get('session_id')}, episode_id={r.get('episode_id')}")

        # Query Neo4j for episodes (use sessionId which is the stored property name)
        neo4j_query = """
        MATCH (e:Episode {sessionId: $session_id})
        RETURN e.episodeId as episode_id, e.summary as summary
        LIMIT 10
        """
        neo4j_results = await neo4j_adapter.execute_query(neo4j_query, {'session_id': test_session_id})
        
        # Verify episodes exist in both stores
        assert len(qdrant_results) > 0, "No episodes found in Qdrant"
        assert len(neo4j_results) > 0, "No episodes found in Neo4j"
        
        # Extract episode IDs from both stores
        qdrant_episode_ids = {hit.get('episode_id') for hit in qdrant_results}
        neo4j_episode_ids = {rec['episode_id'] for rec in neo4j_results}
        
        # Verify overlap (at least one episode in both)
        common_episodes = qdrant_episode_ids & neo4j_episode_ids
        assert len(common_episodes) > 0, f"No common episodes between Qdrant ({len(qdrant_episode_ids)}) and Neo4j ({len(neo4j_episode_ids)})"
        
        # Record results
        report_collector.add_result(
            test_name='test_l2_to_l3_consolidation_with_episode_clustering',
            latencies=latencies,
            provider=provider_name,
            passed=True,
            metadata={
                'facts_stored': len(facts),
                'episodes_created': stats.get('episodes_created', 0),
                'qdrant_episodes': len(qdrant_episode_ids),
                'neo4j_episodes': len(neo4j_episode_ids),
                'common_episodes': len(common_episodes)
            }
        )
        
        print(f"✅ Created episodes indexed in both Qdrant ({len(qdrant_episode_ids)}) and Neo4j ({len(neo4j_episode_ids)})")
        print(f"📊 Common episodes: {len(common_episodes)}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_l3_to_l4_distillation_with_knowledge_synthesis(
        self,
        test_session_id,
        test_user_id,
        neo4j_adapter,
        qdrant_adapter,
        typesense_adapter,
        real_llm_client,
        test_settings,
        report_collector,
        full_cleanup
    ):
        """Test L3→L4 distillation with provenance tracking.
        
        Workflow:
        1. Create 5+ episodes in L3 with session_id/user_id
        2. Run DistillationEngine with track_provenance=True
        3. Query Typesense for knowledge documents
        4. Verify source_episode_ids contains valid L3 references
        5. Verify provenance chain traversable (L4→L3→L2)
        """
        llm_client, provider_name = real_llm_client
        latencies = {}
        
        # 1. Initialize tiers
        l3_tier = EpisodicMemoryTier(qdrant_adapter, neo4j_adapter)
        l4_tier = SemanticMemoryTier(typesense_adapter)
        
        # 2. Create test episodes in L3
        episodes = create_test_episodes(test_session_id, test_user_id, count=5)
        start_store = time.perf_counter()
        for episode in episodes:
            await l3_tier.store({
                'episode': {k: v for k, v in episode.items() if k != 'embedding'},
                'embedding': episode['embedding'],
                'entities': [],
                'relationships': []
            })
        latencies['l3_store_ms'] = (time.perf_counter() - start_store) * 1000
        
        # 3. Create distillation engine
        distillation_engine = DistillationEngine(
            l3_tier=l3_tier,
            l4_tier=l4_tier,
            llm_provider=llm_client,
            config={'distillation_threshold': 5}
        )
        
        # Apply throttle
        await asyncio.sleep(test_settings.llm_throttle_seconds)
        
        # 4. Execute distillation with provenance tracking
        start_distillation = time.perf_counter()
        stats = await distillation_engine.distill(
            session_id=test_session_id,
            track_provenance=True
        )
        latencies['distillation_ms'] = (time.perf_counter() - start_distillation) * 1000
        
        await asyncio.sleep(test_settings.llm_throttle_seconds)
        
        # 5. Query Typesense for knowledge documents
        search_params = {
            'q': '*',
            'query_by': 'content',
            'filter_by': f'session_id:={test_session_id}',
            'limit': 10
        }
        knowledge_docs = await typesense_adapter.search(search_params)
        
        # Verify knowledge documents created
        assert len(knowledge_docs) > 0, "No knowledge documents found in Typesense"
        assert stats.get('knowledge_documents_created', 0) > 0, "Distillation engine reported 0 documents"
        
        # Verify provenance tracking
        for doc in knowledge_docs:
            source_episode_ids = doc.get('source_episode_ids', [])
            assert len(source_episode_ids) > 0, f"Knowledge doc {doc.get('id')} missing source_episode_ids"
            
            # Verify episode IDs are valid (exist in L3)
            for episode_id in source_episode_ids:
                # Check episode exists in Neo4j
                verify_query = "MATCH (e:Episode {episode_id: $eid}) RETURN e.episode_id"
                result = await neo4j_adapter.execute_query(verify_query, {'eid': episode_id})
                assert len(result) > 0, f"Episode {episode_id} not found in Neo4j (broken provenance)"
        
        # Record results
        report_collector.add_result(
            test_name='test_l3_to_l4_distillation_with_knowledge_synthesis',
            latencies=latencies,
            provider=provider_name,
            passed=True,
            metadata={
                'episodes_created': len(episodes),
                'knowledge_docs_created': len(knowledge_docs),
                'distillation_stats': stats
            }
        )
        
        print(f"✅ Distilled {len(knowledge_docs)} knowledge documents from {len(episodes)} episodes using {provider_name}")
        print("📊 Provenance verified for all documents")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_lifecycle_end_to_end(
        self,
        test_session_id,
        test_user_id,
        redis_adapter,
        postgres_adapter,
        neo4j_adapter,
        qdrant_adapter,
        typesense_adapter,
        real_llm_client,
        test_settings,
        report_collector,
        full_cleanup
    ):
        """Test complete L1→L2→L3→L4 flow with latency observation.
        
        Workflow:
        1. Store 50 turns in L1
        2. Promote to L2 (expect ~15 facts)
        3. Consolidate to L3 (expect ~5 episodes)
        4. Distill to L4 (expect ~2 knowledge docs)
        5. Record latency for each phase
        """
        llm_client, provider_name = real_llm_client
        latencies = {}
        
        # Initialize all tiers
        l1_tier = ActiveContextTier(redis_adapter, postgres_adapter)
        l2_tier = WorkingMemoryTier(postgres_adapter)
        l3_tier = EpisodicMemoryTier(qdrant_adapter, neo4j_adapter)
        l4_tier = SemanticMemoryTier(typesense_adapter)
        
        # Initialize engines
        topic_segmenter = TopicSegmenter(llm_client)
        fact_extractor = FactExtractor(llm_client)
        ciar_scorer = CIARScorer()
        
        promotion_engine = PromotionEngine(l1_tier, l2_tier, topic_segmenter, fact_extractor, ciar_scorer)
        consolidation_engine = ConsolidationEngine(l2_tier, l3_tier, llm_client)
        distillation_engine = DistillationEngine(l3_tier, l4_tier, llm_client)
        
        # Phase 1: L1 storage
        turns = create_test_turns(test_session_id, count=50)
        start_l1 = time.perf_counter()
        for turn in turns:
            turn['user_id'] = test_user_id
            await l1_tier.store(turn)
        latencies['l1_store_ms'] = (time.perf_counter() - start_l1) * 1000
        
        await asyncio.sleep(test_settings.llm_throttle_seconds)
        
        # Phase 2: L1→L2 promotion
        start_promotion = time.perf_counter()
        promotion_stats = await promotion_engine.process_session(test_session_id)
        latencies['promotion_ms'] = (time.perf_counter() - start_promotion) * 1000
        
        await asyncio.sleep(test_settings.llm_throttle_seconds)
        
        # Phase 3: L2→L3 consolidation
        start_consolidation = time.perf_counter()
        consolidation_stats = await consolidation_engine.process_session(test_session_id)
        latencies['consolidation_ms'] = (time.perf_counter() - start_consolidation) * 1000
        
        await asyncio.sleep(test_settings.llm_throttle_seconds)
        
        # Phase 4: L3→L4 distillation
        start_distillation = time.perf_counter()
        distillation_stats = await distillation_engine.distill(test_session_id, track_provenance=True)
        latencies['distillation_ms'] = (time.perf_counter() - start_distillation) * 1000
        
        # Verify data flow
        l2_facts = await l2_tier.query_by_session(test_session_id)
        
        # Query L3 episodes
        neo4j_query = "MATCH (e:Episode {session_id: $sid}) RETURN count(e) as count"
        l3_result = await neo4j_adapter.execute_query(neo4j_query, {'sid': test_session_id})
        l3_episode_count = l3_result[0]['count'] if l3_result else 0
        
        # Query L4 knowledge
        l4_search = await typesense_adapter.search({
            'q': '*',
            'query_by': 'content',
            'filter_by': f'session_id:={test_session_id}'
        })
        l4_doc_count = len(l4_search)
        
        # Assertions
        assert len(l2_facts) > 0, "No facts in L2"
        assert l3_episode_count > 0, "No episodes in L3"
        assert l4_doc_count > 0, "No knowledge documents in L4"
        
        # Record results
        report_collector.add_result(
            test_name='test_full_lifecycle_end_to_end',
            latencies=latencies,
            provider=provider_name,
            passed=True,
            metadata={
                'l1_turns': len(turns),
                'l2_facts': len(l2_facts),
                'l3_episodes': l3_episode_count,
                'l4_knowledge_docs': l4_doc_count,
                'promotion_stats': promotion_stats,
                'consolidation_stats': consolidation_stats,
                'distillation_stats': distillation_stats
            }
        )
        
        print(f"✅ Full lifecycle complete: {len(turns)}→{len(l2_facts)}→{l3_episode_count}→{l4_doc_count}")
        print(f"📊 Total latency: {sum(latencies.values()):.2f}ms")
        print(f"📊 Breakdown: L1={latencies['l1_store_ms']:.0f}ms, Promotion={latencies['promotion_ms']:.0f}ms, ")
        print(f"   Consolidation={latencies['consolidation_ms']:.0f}ms, Distillation={latencies['distillation_ms']:.0f}ms")


class TestLifecycleStreams:
    """Test Redis Streams-based lifecycle event coordination."""
    
    @pytest.mark.asyncio
    async def test_promotion_event_triggers_consolidation(
        self,
        test_session_id,
        cleanup_redis_keys
    ):
        """Test that promotion events trigger consolidation automatically.
        
        Workflow:
        1. Subscribe to consolidation stream
        2. Publish promotion event
        3. Verify consolidation event received within 1s
        """
        pytest.skip("Requires lifecycle stream implementation - implement in Phase 3 Week 5")
    
    @pytest.mark.asyncio
    async def test_consolidation_event_triggers_distillation(
        self,
        test_session_id,
        cleanup_redis_keys
    ):
        """Test that consolidation events trigger distillation automatically.
        
        Workflow:
        1. Subscribe to distillation stream
        2. Publish consolidation event
        3. Verify distillation event received within 1s
        """
        pytest.skip("Requires lifecycle stream implementation - implement in Phase 3 Week 5")


class TestCrossNavigationQueries:
    """Test cross-tier navigation queries."""
    
    @pytest.mark.asyncio
    async def test_unified_memory_query_across_all_tiers(
        self,
        test_session_id,
        full_cleanup
    ):
        """Test UnifiedMemorySystem.query_memory() hybrid search.
        
        Workflow:
        1. Seed data in L2, L3, L4
        2. Execute query_memory() with configurable weights
        3. Verify results from all tiers normalized and merged
        4. Verify score normalization (min-max per tier)
        5. Verify weighted ranking
        """
        pytest.skip("Requires full memory system - implement in Phase 3 Week 4")
    
    @pytest.mark.asyncio
    async def test_context_block_assembly_from_l1_and_l2(
        self,
        test_session_id,
        cleanup_redis_keys,
        cleanup_postgres_facts
    ):
        """Test ContextBlock assembly from L1 + L2.
        
        Workflow:
        1. Store 20 turns in L1
        2. Store 30 facts in L2 (varying CIAR scores)
        3. Call get_context_block(max_turns=10, min_ciar=0.6)
        4. Verify 10 recent turns included
        5. Verify only high-CIAR facts included
        6. Verify token count estimation accurate
        """
        pytest.skip("Requires full memory system - implement in Phase 3 Week 4")


class TestNetworkLatencyValidation:
    """Test network latency between distributed cluster nodes.
    
    These tests validate that the system performs acceptably with
    real network latency (Node 1 to Node 2 in research cluster).
    """
    
    @pytest.mark.asyncio
    async def test_cross_node_query_latency_under_threshold(
        self,
        test_session_id
    ):
        """Test that cross-node queries complete within latency thresholds.
        
        ADR-003 Latency Requirements:
        - L1 (Redis): <10ms
        - L2 (PostgreSQL): <100ms
        - L3 (Qdrant + Neo4j): <1000ms
        - L4 (Typesense): <1000ms
        """
        pytest.skip("Requires live cluster with latency measurement - implement in Phase 3 Week 5")
    
    @pytest.mark.asyncio
    async def test_hybrid_query_latency_with_real_network(
        self,
        test_session_id,
        full_cleanup
    ):
        """Test that hybrid cross-tier queries complete within 2s budget.
        
        Budget: L2 (100ms) + L3 (1000ms) + L4 (1000ms) + merging (50ms) = 2150ms
        Target: <2000ms for acceptable user experience
        """
        pytest.skip("Requires live cluster with latency measurement - implement in Phase 3 Week 5")


# ============================================================================
# Placeholder Test Data Factories
# ============================================================================

# Rich supply chain conversation content for LLM fact extraction
SUPPLY_CHAIN_CONVERSATION_TEMPLATES = [
    # User reports shipment issues
    ("user", "I need to check on shipment MAEU{idx:07d}. It was supposed to arrive at the Port of Los Angeles yesterday but I haven't received any updates."),
    ("assistant", "I've located shipment MAEU{idx:07d}. It's currently delayed at customs due to incomplete documentation. The expected clearance time is 48-72 hours."),
    
    # User asks about safety stock
    ("user", "Our safety stock levels for SKU-{idx:05d} are critically low. We're down to 15 days of supply and lead time from the supplier is 30 days."),
    ("assistant", "I recommend placing an emergency order with our backup supplier in Vietnam. They can deliver within 14 days at a 12% premium. I've also flagged this for the procurement team."),
    
    # Carrier delay notification
    ("user", "We just received notification that carrier COSCO is experiencing port congestion in Shanghai. This affects our Q1 inventory replenishment."),
    ("assistant", "I've identified 12 affected shipments totaling $2.3M in inventory value. Alternative routing through Ningbo port adds 5 days transit time but avoids the congestion."),
    
    # Quality control issue
    ("user", "Quality inspection failed for batch BT-{idx:06d}. Found 8% defect rate, exceeding our 2% threshold."),
    ("assistant", "I've initiated a supplier corrective action request (SCAR) and placed a hold on remaining inventory from this batch. Root cause analysis meeting scheduled for tomorrow."),
    
    # Demand forecast update
    ("user", "Marketing just revised Q2 demand forecast upward by 35% for the electronics category due to new product launch."),
    ("assistant", "I've updated the demand planning model. This creates a 45,000 unit gap in our current procurement plan. I recommend activating our contract manufacturing agreement with Flex."),
    
    # Supplier financial risk
    ("user", "Our credit monitoring service flagged supplier ACME-{idx:04d} with deteriorating financial health. They supply 40% of our packaging materials."),
    ("assistant", "I've initiated dual-sourcing evaluation with three alternative suppliers. Estimated qualification time is 6-8 weeks. Recommend building 60-day buffer stock as mitigation."),
    
    # Transportation cost optimization
    ("user", "Freight costs have increased 23% this quarter. We need to optimize our transportation network to stay within budget."),
    ("assistant", "Analysis shows consolidating shipments from 3 distribution centers to 2 regional hubs would reduce costs by $180K annually. Trade-off is 0.5 day increase in average delivery time."),
    
    # Inventory write-off discussion
    ("user", "We have 5,000 units of product XYZ-{idx:05d} that will expire in 30 days. Current sell-through rate won't clear this inventory."),
    ("assistant", "Options: 1) Flash sale at 40% discount (projected recovery: $125K), 2) Donate for tax benefit ($45K), 3) Liquidator sale ($80K). Recommend option 1 given brand positioning."),
    
    # Customs compliance issue
    ("user", "Border control in Germany flagged shipment for missing CE certification on product batch CE-{idx:06d}."),
    ("assistant", "Our compliance team confirmed the certification exists but wasn't included in shipping documents. I've expedited document submission. Expected release in 24-48 hours with no penalties."),
    
    # Warehouse capacity alert
    ("user", "Warehouse WH-{idx:03d} in Chicago is at 95% capacity. We have 3 inbound shipments arriving this week totaling 2,400 pallets."),
    ("assistant", "I've arranged overflow storage at third-party facility 15 miles away. Rate is $0.85/pallet/day. Also initiated review of slow-moving inventory for clearance opportunities."),
]


def create_test_turns(session_id: str, count: int = 10):
    """Create test conversation turns for L1 with rich supply chain content.
    
    Uses realistic supply chain scenarios to trigger meaningful LLM fact extraction.
    Content includes shipment delays, inventory issues, supplier risks, and logistics events.
    """
    turns = []
    templates = SUPPLY_CHAIN_CONVERSATION_TEMPLATES
    
    for i in range(count):
        template_idx = i % len(templates)
        role, content_template = templates[template_idx]
        
        # Format template with index for unique identifiers
        content = content_template.format(idx=i)
        
        turns.append({
            'session_id': session_id,
            'turn_id': i,
            'role': role,
            'content': content,
            'metadata': {'test': True, 'turn_index': i, 'scenario_type': 'supply_chain'},
            'created_at': datetime.now(timezone.utc) - timedelta(minutes=count - i)
        })
    return turns


def create_test_facts(session_id: str, count: int = 20):
    """Create test facts for L2 with varying CIAR scores."""
    facts = []
    for i in range(count):
        # Integration happy-path requires CIAR above threshold
        certainty = 0.85
        impact = 0.75
        
        facts.append({
            'session_id': session_id,
            'fact_id': f"test-fact-{i}",
            'content': f"Test fact {i}: Shipment {i} delayed at customs.",
            'fact_type': 'event',
            'certainty': certainty,
            'impact': impact,
            'ciar_score': certainty * impact,  # Simplified CIAR
            'created_at': datetime.now(timezone.utc) - timedelta(hours=i),
            'access_count': i % 5
        })
    return facts


def create_test_episodes(session_id: str, user_id: str, count: int = 5):
    """Create test episodes for L3 with provenance metadata."""
    import uuid

    def _load_corpus() -> str:
        """Load real text corpus from embedding test data for deterministic vectors."""
        data_dir = Path(__file__).parent.parent / "fixtures" / "embedding_test_data"
        if not data_dir.exists():
            return ""
        texts = []
        for file_path in sorted(data_dir.glob("*")):
            try:
                texts.append(file_path.read_text(encoding="utf-8"))
            except OSError:
                continue
        return "\n\n".join(texts)

    corpus = _load_corpus()

    def _deterministic_embedding(seed_text: str) -> list[float]:
        """Generate a stable pseudo-embedding from real text without padding."""
        vector = []
        target_dim = EpisodicMemoryTier.VECTOR_SIZE
        base = (seed_text or corpus or "fallback").encode("utf-8")
        for i in range(target_dim):
            digest = hashlib.sha256(base + i.to_bytes(4, "little", signed=False)).digest()
            # Use first 8 bytes for a float-ish value in [0,1)
            value = int.from_bytes(digest[:8], "big") / float(2**64)
            vector.append(round(value, 6))
        return vector

    episodes = []
    for i in range(count):
        episode_id = f"test-episode-{uuid.uuid4().hex[:8]}"
        content = f"Episode summarizing shipment tracking events {i*5} through {i*5+4}"
        embedding = _deterministic_embedding(content)
        window_start = datetime.now(timezone.utc) - timedelta(days=i, hours=1)
        window_end = window_start + timedelta(hours=1)
        episodes.append({
            'episode_id': episode_id,
            'session_id': session_id,
            'user_id': user_id,
            'summary': f"Test episode {i}: Port operations and customs delays",
            'content': content,
            'embedding': embedding,
            'fact_ids': [f"test-fact-{i*5+j}" for j in range(5)],  # Link to 5 facts
            'created_at': datetime.now(timezone.utc) - timedelta(days=i),
            'valid_from': datetime.now(timezone.utc) - timedelta(days=i),
            'valid_to': None,
            'time_window_start': window_start,
            'time_window_end': window_end,
            'duration_seconds': (window_end - window_start).total_seconds(),
            'fact_valid_from': window_start,
            'fact_valid_to': window_end,
            'source_observation_timestamp': window_start,
            'metadata': {'test': True, 'episode_index': i}
        })
    return episodes

