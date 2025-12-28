"""
CIAR Tools for Agent Memory Management (ADR-007).

Provides LangChain-compatible tools for CIAR score calculation, filtering,
and explanation. These tools allow agents to understand and manipulate the
significance scoring system that controls memory promotion between tiers.

Tools:
- ciar_calculate: Calculate CIAR score for content with explicit components
- ciar_filter: Batch filter facts by CIAR threshold
- ciar_explain: Get human-readable explanation of CIAR score breakdown
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from datetime import datetime
import json

from langchain_core.tools import tool

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig as ToolRuntime
else:
    try:
        from langchain_core.runnables import RunnableConfig as ToolRuntime
    except ImportError:
        ToolRuntime = Any

from src.agents.runtime import MASToolRuntime
from src.memory.ciar_scorer import CIARScorer


# ============================================================================
# Input Schemas (Pydantic Models)
# ============================================================================

class CIARCalculateInput(BaseModel):
    """Input schema for ciar_calculate tool."""
    content: str = Field(description="Fact content to score (e.g., 'Container MAEU1234567 arrived at Port of LA')")
    certainty: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in fact accuracy (0.0-1.0). Use 0.9 for explicit statements, 0.7 for inferred facts."
    )
    impact: float = Field(
        ge=0.0,
        le=1.0,
        description="Importance/relevance (0.0-1.0). Use 0.9 for critical events, 0.5 for routine updates."
    )
    fact_type: str = Field(
        default="observation",
        description="Fact type: 'entity', 'preference', 'constraint', 'observation', 'event'"
    )
    days_old: int = Field(
        default=0,
        ge=0,
        description="Age of fact in days (0 = today)"
    )
    access_count: int = Field(
        default=0,
        ge=0,
        description="Number of times fact has been accessed (affects recency boost)"
    )


class CIARFilterInput(BaseModel):
    """Input schema for ciar_filter tool."""
    facts: List[Dict[str, Any]] = Field(
        description="List of fact dictionaries with keys: content, certainty, impact, fact_type, created_at, access_count"
    )
    min_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum CIAR score threshold (default: 0.6)"
    )
    return_scores: bool = Field(
        default=True,
        description="Include calculated scores in output"
    )


class CIARExplainInput(BaseModel):
    """Input schema for ciar_explain tool."""
    content: str = Field(description="Fact content to explain")
    certainty: float = Field(ge=0.0, le=1.0, description="Certainty value")
    impact: float = Field(ge=0.0, le=1.0, description="Impact value")
    fact_type: str = Field(default="observation", description="Fact type")
    days_old: int = Field(default=0, ge=0, description="Age in days")
    access_count: int = Field(default=0, ge=0, description="Access count")


# ============================================================================
# Tool Implementations
# ============================================================================

@tool(args_schema=CIARCalculateInput)
async def ciar_calculate(
    content: str,
    certainty: float,
    impact: float,
    fact_type: str = "observation",
    days_old: int = 0,
    access_count: int = 0,
    runtime: ToolRuntime = None
) -> str:
    """
    Calculate CIAR score for a fact with explicit components.
    
    Use this tool to determine if a fact is significant enough for promotion
    to L2 Working Memory (threshold: 0.6). The CIAR score combines certainty,
    impact, age decay, and recency boost.
    
    Formula: (Certainty × Impact) × Age_Decay × Recency_Boost
    
    Returns JSON with final_score, all components, and promotion eligibility.
    """
    try:
        mas_runtime = MASToolRuntime(runtime)
        await mas_runtime.stream_status(f"Calculating CIAR score for: {content[:50]}...")
        
        # Initialize scorer
        scorer = CIARScorer()
        
        # Build fact dict with current timestamp offset by days_old
        from datetime import timedelta, timezone
        created_at = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        fact_dict = {
            'content': content,
            'certainty': certainty,
            'impact': impact,
            'fact_type': fact_type,
            'created_at': created_at,
            'access_count': access_count
        }
        
        # Calculate components
        components = scorer.calculate_components(fact_dict)
        
        # Determine promotion eligibility
        final_score = components['final_score']
        threshold = scorer.threshold
        is_promotable = final_score >= threshold
        
        result = {
            'content': content[:100] + '...' if len(content) > 100 else content,
            'final_score': round(final_score, 4),
            'threshold': threshold,
            'is_promotable': is_promotable,
            'components': {
                'certainty': round(components['certainty'], 4),
                'impact': round(components['impact'], 4),
                'age_decay': round(components['age_decay'], 4),
                'recency_boost': round(components['recency_boost'], 4),
                'base_score': round(components['base_score'], 4),
                'temporal_score': round(components['temporal_score'], 4)
            },
            'verdict': (
                f"✅ Score {final_score:.3f} exceeds threshold {threshold} - PROMOTE to L2"
                if is_promotable else
                f"❌ Score {final_score:.3f} below threshold {threshold} - REJECT"
            )
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error calculating CIAR score: {str(e)}"


@tool(args_schema=CIARFilterInput)
async def ciar_filter(
    facts: List[Dict[str, Any]],
    min_threshold: float = 0.6,
    return_scores: bool = True,
    runtime: ToolRuntime = None
) -> str:
    """
    Batch filter facts by CIAR score threshold.
    
    Use this tool to filter a list of facts and keep only those that meet
    the significance threshold for L2 Working Memory promotion.
    
    Returns JSON with filtered facts, statistics, and optional scores.
    """
    try:
        mas_runtime = MASToolRuntime(runtime)
        await mas_runtime.stream_status(f"Filtering {len(facts)} facts by CIAR threshold {min_threshold}...")
        
        scorer = CIARScorer()
        
        # Process each fact
        results = []
        for fact in facts:
            # Ensure created_at is datetime
            if 'created_at' in fact and isinstance(fact['created_at'], str):
                fact['created_at'] = datetime.fromisoformat(fact['created_at'].replace('Z', '+00:00'))
            
            score = scorer.calculate(fact)
            
            if score >= min_threshold:
                result_fact = fact.copy()
                if return_scores:
                    result_fact['ciar_score'] = round(score, 4)
                results.append(result_fact)
        
        # Build response
        response = {
            'input_count': len(facts),
            'filtered_count': len(results),
            'pass_rate': round(len(results) / len(facts) * 100, 1) if facts else 0.0,
            'threshold': min_threshold,
            'facts': results
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        return f"Error filtering facts by CIAR: {str(e)}"


@tool(args_schema=CIARExplainInput)
async def ciar_explain(
    content: str,
    certainty: float,
    impact: float,
    fact_type: str = "observation",
    days_old: int = 0,
    access_count: int = 0,
    runtime: ToolRuntime = None
) -> str:
    """
    Get human-readable explanation of CIAR score breakdown.
    
    Use this tool to understand WHY a fact received a specific CIAR score.
    Returns detailed explanation of each component and how they combine.
    """
    try:
        mas_runtime = MASToolRuntime(runtime)
        
        # Initialize scorer
        scorer = CIARScorer()
        
        # Build fact dict
        from datetime import timedelta, timezone
        created_at = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        fact_dict = {
            'content': content,
            'certainty': certainty,
            'impact': impact,
            'fact_type': fact_type,
            'created_at': created_at,
            'access_count': access_count
        }
        
        # Calculate components
        components = scorer.calculate_components(fact_dict)
        
        # Build explanation
        explanation = []
        explanation.append(f"CIAR Score Breakdown for: '{content[:80]}...'")
        explanation.append("=" * 70)
        explanation.append("")
        
        # Component explanations
        explanation.append(f"1. Certainty (C): {components['certainty']:.4f}")
        explanation.append(f"   → Confidence in fact accuracy")
        explanation.append(f"   → Input value: {certainty} (explicit)")
        explanation.append("")
        
        explanation.append(f"2. Impact (I): {components['impact']:.4f}")
        explanation.append(f"   → Importance/relevance of fact")
        explanation.append(f"   → Input value: {impact} (fact_type: {fact_type})")
        explanation.append("")
        
        explanation.append(f"3. Age Decay (AD): {components['age_decay']:.4f}")
        explanation.append(f"   → Time-based decay factor")
        explanation.append(f"   → Age: {days_old} days old")
        explanation.append(f"   → Formula: exp(-λ × days) where λ={scorer.age_decay_lambda}")
        explanation.append("")
        
        explanation.append(f"4. Recency Boost (RB): {components['recency_boost']:.4f}")
        explanation.append(f"   → Access frequency reward")
        explanation.append(f"   → Access count: {access_count}")
        explanation.append(f"   → Formula: 1 + (α × log(1 + count)) where α={scorer.recency_boost_factor}")
        explanation.append("")
        
        # Calculation steps
        explanation.append("Calculation:")
        explanation.append("-" * 70)
        explanation.append(f"Base Score = C × I = {components['certainty']:.4f} × {components['impact']:.4f} = {components['base_score']:.4f}")
        explanation.append(f"Temporal Score = AD × RB = {components['age_decay']:.4f} × {components['recency_boost']:.4f} = {components['temporal_score']:.4f}")
        explanation.append(f"Final CIAR Score = Base × Temporal = {components['base_score']:.4f} × {components['temporal_score']:.4f} = {components['final_score']:.4f}")
        explanation.append("")
        
        # Verdict
        threshold = scorer.threshold
        is_promotable = components['final_score'] >= threshold
        explanation.append("Verdict:")
        explanation.append("-" * 70)
        if is_promotable:
            explanation.append(f"✅ PROMOTE to L2 Working Memory")
            explanation.append(f"   Score {components['final_score']:.4f} exceeds threshold {threshold}")
        else:
            margin = threshold - components['final_score']
            explanation.append(f"❌ REJECT (Stay in L1 or discard)")
            explanation.append(f"   Score {components['final_score']:.4f} below threshold {threshold}")
            explanation.append(f"   Needs +{margin:.4f} to qualify")
        
        return "\n".join(explanation)
        
    except Exception as e:
        return f"Error explaining CIAR score: {str(e)}"


# ============================================================================
# Tool Metadata (for export)
# ============================================================================

CIAR_TOOLS = [ciar_calculate, ciar_filter, ciar_explain]
