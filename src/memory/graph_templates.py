"""
Graph Query Templates for L3 Episodic Memory (ADR-003).

This module provides template-based Cypher queries with hard-coded temporal
validity checks to prevent "temporal amnesia" where agents query outdated
relationships.

All templates enforce the bi-temporal model constraint:
    WHERE r.factValidTo IS NULL

This ensures agents always query the CURRENT state of the world, not
historical snapshots (unless explicitly using temporal queries).

Design Rationale:
1. **Prevent Temporal Amnesia**: Hard-code temporal validity in templates
2. **Schema Consistency**: Constrain agents to valid relationship types
3. **Security**: Use parameter injection ($param) to prevent Cypher injection
4. **Domain Focus**: Templates optimized for international container logistics

Template Categories:
- Container/Shipment Tracking
- Multi-Party Relationships
- Causal Analysis
- Document Flow
- Timeline Queries
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class TemplateCategory(str, Enum):
    """Template categories for organizing queries."""
    TRACKING = "tracking"
    RELATIONSHIPS = "relationships"
    CAUSALITY = "causality"
    DOCUMENTS = "documents"
    TEMPORAL = "temporal"


@dataclass
class GraphQueryTemplate:
    """
    Template for safe, parameterized Neo4j Cypher queries.
    
    All templates enforce temporal validity (factValidTo IS NULL) to
    prevent querying outdated relationships.
    
    Attributes:
        name: Unique template identifier (e.g., 'get_container_journey')
        cypher_template: Cypher query with $parameters
        required_params: List of parameter names that must be provided
        optional_params: Dict of optional parameters with defaults
        description: Human-readable description for LLM agents
        category: Template category for organization
        returns: Description of return structure
        examples: Example parameter sets for documentation
    """
    name: str
    cypher_template: str
    required_params: List[str]
    optional_params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    category: TemplateCategory = TemplateCategory.TRACKING
    returns: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)
    
    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate that all required parameters are provided.
        
        Args:
            params: Parameter dict to validate
        
        Returns:
            (is_valid, error_message)
        """
        missing = [p for p in self.required_params if p not in params]
        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"
        return True, None
    
    def merge_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge provided params with optional defaults.
        
        Args:
            params: User-provided parameters
        
        Returns:
            Complete parameter dict with defaults filled in
        """
        merged = self.optional_params.copy()
        merged.update(params)
        return merged


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

# Container/Shipment Tracking Templates
GET_CONTAINER_JOURNEY = GraphQueryTemplate(
    name="get_container_journey",
    cypher_template="""
        MATCH path = (container:Container {container_id: $container_id})
                     -[r:MOVED_TO|LOADED_ON|UNLOADED_FROM*1..20]->
                     (destination)
        WHERE ALL(rel IN relationships(path) WHERE rel.factValidTo IS NULL)
          AND container.factValidTo IS NULL
        WITH path, length(path) as hop_count
        ORDER BY hop_count DESC
        LIMIT $max_hops
        RETURN path,
               [node IN nodes(path) | {
                   id: node.entity_id,
                   type: labels(node)[0],
                   name: node.name,
                   location: node.location
               }] as journey_nodes,
               [rel IN relationships(path) | {
                   type: type(rel),
                   timestamp: rel.timestamp,
                   episode_id: rel.episode_id
               }] as journey_edges
    """,
    required_params=["container_id"],
    optional_params={"max_hops": 20},
    description="Track a container's journey through ports, vessels, and facilities",
    category=TemplateCategory.TRACKING,
    returns="Path with nodes (ports, vessels, facilities) and edges (movements)",
    examples=[
        {"container_id": "MAEU1234567", "max_hops": 15},
        {"container_id": "CMAU5678901"}
    ]
)

GET_SHIPMENT_PARTIES = GraphQueryTemplate(
    name="get_shipment_parties",
    cypher_template="""
        MATCH (shipment:Shipment {shipment_id: $shipment_id})
        WHERE shipment.factValidTo IS NULL
        OPTIONAL MATCH (shipment)-[r_shipper:SHIPPED_BY]->(shipper:Organization)
        WHERE r_shipper.factValidTo IS NULL AND shipper.factValidTo IS NULL
        OPTIONAL MATCH (shipment)-[r_consignee:CONSIGNED_TO]->(consignee:Organization)
        WHERE r_consignee.factValidTo IS NULL AND consignee.factValidTo IS NULL
        OPTIONAL MATCH (shipment)-[r_carrier:CARRIED_BY]->(carrier:Organization)
        WHERE r_carrier.factValidTo IS NULL AND carrier.factValidTo IS NULL
        OPTIONAL MATCH (shipment)-[r_agent:REPRESENTED_BY]->(agent:Organization)
        WHERE r_agent.factValidTo IS NULL AND agent.factValidTo IS NULL
        RETURN shipment,
               {
                   shipper: {id: shipper.entity_id, name: shipper.name, country: shipper.country},
                   consignee: {id: consignee.entity_id, name: consignee.name, country: consignee.country},
                   carrier: {id: carrier.entity_id, name: carrier.name, scac: carrier.scac_code},
                   agent: {id: agent.entity_id, name: agent.name, role: agent.role}
               } as parties
    """,
    required_params=["shipment_id"],
    optional_params={},
    description="Get all parties (shipper, consignee, carrier, agent) for a shipment",
    category=TemplateCategory.RELATIONSHIPS,
    returns="Shipment node and dict of all related parties",
    examples=[
        {"shipment_id": "SHP-2024-001234"}
    ]
)

FIND_DELAY_CAUSES = GraphQueryTemplate(
    name="find_delay_causes",
    cypher_template="""
        MATCH (shipment:Shipment {shipment_id: $shipment_id})
              -[r_delayed:DELAYED_BY*1..$max_depth]->(cause)
        WHERE shipment.factValidTo IS NULL
          AND ALL(rel IN r_delayed WHERE rel.factValidTo IS NULL)
        WITH shipment, cause, r_delayed
        ORDER BY length(r_delayed) ASC
        RETURN shipment,
               cause,
               [rel IN r_delayed | {
                   type: type(rel),
                   reason: rel.reason,
                   delay_hours: rel.delay_hours,
                   timestamp: rel.timestamp,
                   episode_id: rel.episode_id
               }] as causal_chain,
               length(r_delayed) as causal_depth
        LIMIT $max_results
    """,
    required_params=["shipment_id"],
    optional_params={"max_depth": 5, "max_results": 10},
    description="Find causal chain of delay reasons for a shipment",
    category=TemplateCategory.CAUSALITY,
    returns="Shipment, root cause, and causal chain of delay relationships",
    examples=[
        {"shipment_id": "SHP-2024-001234", "max_depth": 3},
        {"shipment_id": "SHP-2024-005678", "max_results": 5}
    ]
)

GET_DOCUMENT_FLOW = GraphQueryTemplate(
    name="get_document_flow",
    cypher_template="""
        MATCH (shipment:Shipment {shipment_id: $shipment_id})
        WHERE shipment.factValidTo IS NULL
        OPTIONAL MATCH path = (shipment)-[r_doc:HAS_DOCUMENT|REQUIRES_DOCUMENT*1..10]->(doc:Document)
        WHERE ALL(rel IN relationships(path) WHERE rel.factValidTo IS NULL)
          AND doc.factValidTo IS NULL
        WITH shipment, doc, path
        ORDER BY doc.timestamp ASC
        RETURN shipment,
               COLLECT({
                   document_id: doc.document_id,
                   document_type: doc.document_type,
                   status: doc.status,
                   issued_at: doc.timestamp,
                   issued_by: doc.issued_by,
                   path_length: length(path)
               }) as documents
    """,
    required_params=["shipment_id"],
    optional_params={},
    description="Get all documents (Bill of Lading, customs forms, delivery proof) for a shipment",
    category=TemplateCategory.DOCUMENTS,
    returns="Shipment and ordered list of associated documents",
    examples=[
        {"shipment_id": "SHP-2024-001234"}
    ]
)

GET_RELATED_EPISODES = GraphQueryTemplate(
    name="get_related_episodes",
    cypher_template="""
        MATCH (entity {entity_id: $entity_id})
        WHERE entity.factValidTo IS NULL
        MATCH (entity)-[r]-(related)
        WHERE r.factValidTo IS NULL
          AND related.factValidTo IS NULL
          AND r.timestamp >= datetime($start_time)
          AND r.timestamp <= datetime($end_time)
        WITH entity, r, related, r.episode_id as episode_id
        ORDER BY r.timestamp DESC
        RETURN DISTINCT episode_id,
               r.timestamp as timestamp,
               type(r) as relationship_type,
               {
                   id: related.entity_id,
                   type: labels(related)[0],
                   name: COALESCE(related.name, related.entity_id)
               } as related_entity
        LIMIT $max_results
    """,
    required_params=["entity_id", "start_time", "end_time"],
    optional_params={"max_results": 50},
    description="Find all episodes (events) involving an entity within a time window",
    category=TemplateCategory.TEMPORAL,
    returns="List of episodes with timestamps and related entities",
    examples=[
        {
            "entity_id": "MAEU1234567",
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-12-31T23:59:59Z",
            "max_results": 20
        }
    ]
)

GET_ENTITY_TIMELINE = GraphQueryTemplate(
    name="get_entity_timeline",
    cypher_template="""
        MATCH (entity {entity_id: $entity_id})
        WHERE entity.factValidTo IS NULL
        MATCH (entity)-[r]-(other)
        WHERE r.factValidTo IS NULL
          AND other.factValidTo IS NULL
        WITH entity, r, other
        ORDER BY r.timestamp ASC
        RETURN {
            timestamp: r.timestamp,
            event_type: type(r),
            episode_id: r.episode_id,
            related_entity: {
                id: other.entity_id,
                type: labels(other)[0],
                name: COALESCE(other.name, other.entity_id)
            },
            metadata: {
                location: r.location,
                status: r.status,
                description: r.description
            }
        } as timeline_event
        LIMIT $max_events
    """,
    required_params=["entity_id"],
    optional_params={"max_events": 100},
    description="Get chronological timeline of all events for an entity (container, shipment, etc.)",
    category=TemplateCategory.TEMPORAL,
    returns="Ordered list of timeline events with timestamps and related entities",
    examples=[
        {"entity_id": "MAEU1234567", "max_events": 50},
        {"entity_id": "SHP-2024-001234"}
    ]
)


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

TEMPLATE_REGISTRY: Dict[str, GraphQueryTemplate] = {
    "get_container_journey": GET_CONTAINER_JOURNEY,
    "get_shipment_parties": GET_SHIPMENT_PARTIES,
    "find_delay_causes": FIND_DELAY_CAUSES,
    "get_document_flow": GET_DOCUMENT_FLOW,
    "get_related_episodes": GET_RELATED_EPISODES,
    "get_entity_timeline": GET_ENTITY_TIMELINE,
}


def get_template(name: str) -> Optional[GraphQueryTemplate]:
    """
    Retrieve a query template by name.
    
    Args:
        name: Template name (e.g., 'get_container_journey')
    
    Returns:
        GraphQueryTemplate or None if not found
    """
    return TEMPLATE_REGISTRY.get(name)


def list_templates(category: Optional[TemplateCategory] = None) -> List[GraphQueryTemplate]:
    """
    List all available templates, optionally filtered by category.
    
    Args:
        category: Optional category filter
    
    Returns:
        List of matching templates
    """
    templates = list(TEMPLATE_REGISTRY.values())
    if category:
        templates = [t for t in templates if t.category == category]
    return templates


def validate_and_execute_template(
    name: str,
    params: Dict[str, Any]
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Validate template exists and parameters are complete.
    
    Args:
        name: Template name
        params: Parameters to validate
    
    Returns:
        (is_valid, error_message, cypher_query)
        If valid, returns (True, None, cypher_query)
        If invalid, returns (False, error_message, None)
    """
    template = get_template(name)
    if not template:
        available = ", ".join(TEMPLATE_REGISTRY.keys())
        return False, f"Unknown template '{name}'. Available: {available}", None
    
    is_valid, error_msg = template.validate_params(params)
    if not is_valid:
        return False, error_msg, None
    
    return True, None, template.cypher_template
