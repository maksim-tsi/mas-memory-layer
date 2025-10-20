"""
Synthetic workload generator for storage adapter benchmarking.

Generates realistic operation patterns matching production memory access patterns
across L1/L2 cache and L3 specialized storage layers.
"""

import random
import string
import uuid
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


@dataclass
class WorkloadOperation:
    """Single operation in a benchmark workload."""
    op_type: str  # 'store', 'retrieve', 'search', 'delete'
    adapter: str  # 'redis_l1', 'redis_l2', 'qdrant', 'neo4j', 'typesense'
    data: Optional[Dict[str, Any]] = None
    query: Optional[Dict[str, Any]] = None
    item_id: Optional[str] = None


class WorkloadGenerator:
    """
    Generate synthetic but realistic workload for storage adapters.
    
    Workload Distribution (based on typical agent memory access patterns):
    - 40% L1 cache operations (Redis) - hot data, frequent access
    - 30% L2 cache operations (Redis) - warm data, moderate access
    - 15% L3 semantic search (Qdrant) - vector similarity queries
    - 10% L3 graph traversal (Neo4j) - relationship queries
    - 5% L3 full-text search (Typesense) - keyword searches
    
    Operation Mix:
    - 70% reads (retrieve/search)
    - 25% writes (store)
    - 5% deletes
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize workload generator.
        
        Args:
            seed: Random seed for reproducible workloads
        """
        if seed is not None:
            random.seed(seed)
        
        self.session_ids = [f"session-{i}" for i in range(10)]  # 10 test sessions
        self.stored_ids = {
            'redis_l1': [],
            'redis_l2': [],
            'qdrant': [],
            'neo4j': [],
            'typesense': []
        }
        # Separate tracking for Neo4j entity IDs (for relationship referential integrity)
        self.neo4j_entity_ids = []
    
    def generate_workload(
        self,
        size: int = 10000,
        distribution: Optional[Dict[str, float]] = None
    ) -> List[WorkloadOperation]:
        """
        Generate workload with specified size and distribution.
        
        Args:
            size: Total number of operations to generate
            distribution: Custom distribution override (adapter -> probability)
                        Default: {'redis_l1': 0.40, 'redis_l2': 0.30,
                                 'qdrant': 0.15, 'neo4j': 0.10, 'typesense': 0.05}
        
        Returns:
            List of WorkloadOperation objects
        """
        if distribution is None:
            distribution = {
                'redis_l1': 0.40,
                'redis_l2': 0.30,
                'qdrant': 0.15,
                'neo4j': 0.10,
                'typesense': 0.05
            }
        
        operations = []
        
        for i in range(size):
            # Select adapter based on distribution
            adapter = self._select_adapter(distribution)
            
            # Select operation type (70% read, 25% write, 5% delete)
            op_rand = random.random()
            
            if op_rand < 0.25:  # 25% writes
                op = self._generate_store_op(adapter)
                operations.append(op)
            elif op_rand < 0.90:  # 65% reads (70% - 5%)
                # Mix of retrieve and search
                if random.random() < 0.5 and self.stored_ids[adapter]:
                    operations.append(self._generate_retrieve_op(adapter))
                else:
                    operations.append(self._generate_search_op(adapter))
            else:  # 10% deletes (5% actual, rest becomes no-op if nothing to delete)
                if self.stored_ids[adapter]:
                    operations.append(self._generate_delete_op(adapter))
                else:
                    # If nothing to delete, do a read instead
                    operations.append(self._generate_search_op(adapter))
        
        # === POST-GENERATION PHASE: Neo4j Relationships ===
        # Now that all entities exist, generate relationships from the complete entity pool
        # This ensures perfect referential integrity - all relationships reference existing entities
        if self.neo4j_entity_ids:
            # Calculate number of relationships to generate (aim for ~30% of entities)
            # This maintains realistic graph density while ensuring good test coverage
            num_relationships = max(1, int(len(self.neo4j_entity_ids) * 0.3))
            
            for _ in range(num_relationships):
                # Select two random entities from the complete pool
                from_id = random.choice(self.neo4j_entity_ids)
                to_id = random.choice(self.neo4j_entity_ids)
                
                # Generate relationship between these entities
                rel_op = self._generate_neo4j_relationship(from_id, to_id)
                operations.append(rel_op)
        
        return operations
    
    def _select_adapter(self, distribution: Dict[str, float]) -> str:
        """Select adapter based on probability distribution."""
        rand = random.random()
        cumulative = 0.0
        
        for adapter, prob in distribution.items():
            cumulative += prob
            if rand < cumulative:
                return adapter
        
        return 'redis_l1'  # Fallback
    
    # === Store Operation Generators ===
    
    def _generate_store_op(self, adapter: str) -> WorkloadOperation:
        """Generate store operation for given adapter."""
        if adapter in ['redis_l1', 'redis_l2']:
            return self._generate_redis_store(adapter)
        elif adapter == 'qdrant':
            return self._generate_qdrant_store()
        elif adapter == 'neo4j':
            return self._generate_neo4j_store()
        elif adapter == 'typesense':
            return self._generate_typesense_store()
        else:
            raise ValueError(f"Unknown adapter: {adapter}")
    
    def _generate_redis_store(self, adapter: str) -> WorkloadOperation:
        """Generate Redis store operation (conversation turn)."""
        session_id = random.choice(self.session_ids)
        turn_id = len([op for op in self.stored_ids[adapter] if session_id in str(op)])
        
        data = {
            'session_id': session_id,
            'turn_id': turn_id,
            'content': self._random_text(50, 200),
            'role': random.choice(['user', 'assistant']),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Track stored ID (using session_id as proxy)
        self.stored_ids[adapter].append(f"{session_id}:{turn_id}")
        
        return WorkloadOperation(
            op_type='store',
            adapter=adapter,
            data=data
        )
    
    def _generate_qdrant_store(self) -> WorkloadOperation:
        """Generate Qdrant store operation (vector embedding)."""
        doc_id = str(uuid.uuid4())
        
        data = {
            'id': doc_id,
            'vector': [random.random() for _ in range(384)],  # 384-dim embedding
            'content': self._random_text(100, 500),  # Required field at top level
            'session_id': random.choice(self.session_ids),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.stored_ids['qdrant'].append(doc_id)
        
        return WorkloadOperation(
            op_type='store',
            adapter='qdrant',
            data=data
        )
    
    def _generate_neo4j_store(self) -> WorkloadOperation:
        """
        Generate Neo4j store operation (entity only - relationships generated separately).
        
        This method now ONLY creates entity nodes. Relationships are generated in a separate
        phase after all entities exist, ensuring referential integrity.
        """
        return self._generate_neo4j_entity()
    
    def _generate_neo4j_entity(self) -> WorkloadOperation:
        """Generate Neo4j entity node."""
        entity_id = str(uuid.uuid4())
        
        data = {
            'type': 'entity',
            'label': random.choice(['Person', 'Topic', 'Event', 'Concept']),
            'properties': {
                'name': self._random_text(5, 20),
                'session_id': random.choice(self.session_ids),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Track entity ID for relationship generation later
        self.neo4j_entity_ids.append(entity_id)
        self.stored_ids['neo4j'].append(entity_id)
        
        return WorkloadOperation(
            op_type='store',
            adapter='neo4j',
            data=data
        )
    
    def _generate_neo4j_relationship(self, from_id: str, to_id: str) -> WorkloadOperation:
        """
        Generate Neo4j relationship between two existing entities.
        
        Args:
            from_id: Source entity ID (must exist in neo4j_entity_ids)
            to_id: Target entity ID (must exist in neo4j_entity_ids)
        
        Returns:
            WorkloadOperation for relationship creation
        """
        relationship_id = str(uuid.uuid4())
        
        data = {
            'type': 'relationship',
            'label': random.choice(['Person', 'Topic', 'Event', 'Concept']),  # Kept for consistency
            'from': from_id,
            'to': to_id,
            'relationship': random.choice(['KNOWS', 'RELATED_TO', 'MENTIONS', 'FOLLOWS']),
            'properties': {
                'session_id': random.choice(self.session_ids),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }
        
        self.stored_ids['neo4j'].append(relationship_id)
        
        return WorkloadOperation(
            op_type='store',
            adapter='neo4j',
            data=data
        )
    
    def _generate_typesense_store(self) -> WorkloadOperation:
        """Generate Typesense store operation (document)."""
        doc_id = str(uuid.uuid4())
        
        data = {
            'id': doc_id,
            'session_id': random.choice(self.session_ids),
            'content': self._random_text(100, 1000),
            'title': self._random_text(5, 50),
            'timestamp': int(datetime.now(timezone.utc).timestamp())
        }
        
        self.stored_ids['typesense'].append(doc_id)
        
        return WorkloadOperation(
            op_type='store',
            adapter='typesense',
            data=data
        )
    
    # === Retrieve Operation Generators ===
    
    def _generate_retrieve_op(self, adapter: str) -> WorkloadOperation:
        """Generate retrieve operation for given adapter."""
        item_id = random.choice(self.stored_ids[adapter])
        
        return WorkloadOperation(
            op_type='retrieve',
            adapter=adapter,
            item_id=item_id
        )
    
    # === Search Operation Generators ===
    
    def _generate_search_op(self, adapter: str) -> WorkloadOperation:
        """Generate search operation for given adapter."""
        if adapter in ['redis_l1', 'redis_l2']:
            return self._generate_redis_search(adapter)
        elif adapter == 'qdrant':
            return self._generate_qdrant_search()
        elif adapter == 'neo4j':
            return self._generate_neo4j_search()
        elif adapter == 'typesense':
            return self._generate_typesense_search()
        else:
            raise ValueError(f"Unknown adapter: {adapter}")
    
    def _generate_redis_search(self, adapter: str) -> WorkloadOperation:
        """Generate Redis search operation (get recent turns)."""
        query = {
            'session_id': random.choice(self.session_ids),
            'limit': random.choice([5, 10, 20])
        }
        
        return WorkloadOperation(
            op_type='search',
            adapter=adapter,
            query=query
        )
    
    def _generate_qdrant_search(self) -> WorkloadOperation:
        """Generate Qdrant search operation (vector similarity)."""
        query = {
            'vector': [random.random() for _ in range(384)],
            'limit': random.choice([5, 10, 20]),
            'filter': {
                'session_id': random.choice(self.session_ids)
            } if random.random() < 0.5 else None
        }
        
        return WorkloadOperation(
            op_type='search',
            adapter='qdrant',
            query=query
        )
    
    def _generate_neo4j_search(self) -> WorkloadOperation:
        """Generate Neo4j search operation (graph query)."""
        query = {
            'cypher': f"MATCH (n) WHERE n.session_id = $session_id RETURN n LIMIT {random.choice([5, 10, 20])}",
            'params': {'session_id': random.choice(self.session_ids)}
        }
        
        return WorkloadOperation(
            op_type='search',
            adapter='neo4j',
            query=query
        )
    
    def _generate_typesense_search(self) -> WorkloadOperation:
        """Generate Typesense search operation (full-text)."""
        query = {
            'q': self._random_text(1, 5),  # Short search query
            'query_by': 'content,title',
            'filter_by': f'session_id:={random.choice(self.session_ids)}' if random.random() < 0.5 else None,
            'per_page': random.choice([5, 10, 20])
        }
        
        return WorkloadOperation(
            op_type='search',
            adapter='typesense',
            query=query
        )
    
    # === Delete Operation Generators ===
    
    def _generate_delete_op(self, adapter: str) -> WorkloadOperation:
        """Generate delete operation for given adapter."""
        item_id = self.stored_ids[adapter].pop(random.randrange(len(self.stored_ids[adapter])))
        
        return WorkloadOperation(
            op_type='delete',
            adapter=adapter,
            item_id=item_id
        )
    
    # === Helper Methods ===
    
    def _random_text(self, min_words: int, max_words: int) -> str:
        """Generate random text with specified word count range."""
        num_words = random.randint(min_words, max_words)
        words = []
        
        for _ in range(num_words):
            word_len = random.randint(3, 12)
            words.append(''.join(random.choices(string.ascii_lowercase, k=word_len)))
        
        return ' '.join(words)


def create_workload_config(name: str, size: int, seed: int = 42) -> Dict[str, Any]:
    """
    Create workload configuration.
    
    Args:
        name: Workload name (e.g., 'small', 'medium', 'large')
        size: Number of operations
        seed: Random seed for reproducibility
    
    Returns:
        Configuration dictionary
    """
    return {
        'name': name,
        'size': size,
        'seed': seed,
        'distribution': {
            'redis_l1': 0.40,
            'redis_l2': 0.30,
            'qdrant': 0.15,
            'neo4j': 0.10,
            'typesense': 0.05
        }
    }
