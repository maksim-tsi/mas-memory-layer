"""
CIAR Scoring System for Memory Promotion

Implements the Certainty-Impact-Age-Recency (CIAR) scoring algorithm
as specified in ADR-003. Calculates scores to determine which facts
should be promoted from L1 (Active Context) to L2 (Working Memory).

Formula: CIAR = (Certainty × Impact) × Age_Decay × Recency_Boost

Components:
- Certainty (C): Confidence in the fact's accuracy (0.0-1.0)
- Impact (I): Importance/relevance of the fact (0.0-1.0)
- Age Decay (AD): Time-based decay factor (0.1-1.0)
- Recency Boost (RB): Access-based reinforcement (1.0-1.3)

Author: MAS Memory Layer Team
Date: November 2025
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
import yaml
from pathlib import Path

from src.memory.models import Fact


class CIARScorer:
    """
    Calculate CIAR scores for facts to determine promotion eligibility.
    
    The CIAR score combines multiple factors to assess a fact's value:
    - How certain/reliable is it?
    - How impactful/important is it?
    - How recent is it? (older = lower)
    - How frequently accessed? (more = higher)
    
    Example:
        >>> scorer = CIARScorer()
        >>> fact = {
        ...     'content': 'User prefers morning meetings',
        ...     'fact_type': 'preference',
        ...     'certainty': 0.9,
        ...     'created_at': datetime.now(),
        ...     'access_count': 5
        ... }
        >>> score = scorer.calculate(fact)
        >>> print(f"CIAR Score: {score:.3f}")
        CIAR Score: 0.756
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the CIAR scorer with configuration.
        
        Args:
            config_path: Path to ciar_config.yaml, defaults to config/ciar_config.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "ciar_config.yaml"
        else:
            config_path = Path(config_path)
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.config = config['ciar']
        self.threshold = self.config['threshold']
        
        # Age decay parameters
        self.age_decay_lambda = self.config['age_decay']['lambda']
        self.max_age_days = self.config['age_decay']['max_age_days']
        self.min_age_score = self.config['age_decay']['min_score']
        
        # Recency boost parameters
        self.recency_boost_factor = self.config['recency']['boost_factor']
        self.max_recency_boost = self.config['recency']['max_boost']
        
        # Certainty parameters
        self.default_certainty = self.config['certainty']['default']
        self.certainty_heuristics = self.config['certainty']
        
        # Impact weights
        self.impact_weights = self.config['impact_weights']
    
    def calculate(self, fact: Union[Dict[str, Any], Fact]) -> float:
        """
        Calculate the complete CIAR score for a fact.
        
        Formula: (Certainty × Impact) × Age_Decay × Recency_Boost
        
        Args:
            fact: Fact dictionary or Fact model instance
        
        Returns:
            float: CIAR score (typically 0.0-1.0, can exceed 1.0 with high recency boost)
        
        Example:
            >>> fact = {'content': 'Test', 'fact_type': 'preference', 
            ...         'certainty': 0.8, 'created_at': datetime.now()}
            >>> score = scorer.calculate(fact)
            >>> assert 0.0 <= score <= 1.5
        """
        # Convert Fact model to dict if needed
        if isinstance(fact, Fact):
            fact_dict = fact.model_dump()
        else:
            fact_dict = fact
        
        # Calculate components
        certainty = self._calculate_certainty(fact_dict)
        impact = self._calculate_impact(fact_dict)
        age_decay = self._calculate_age_decay(fact_dict)
        recency_boost = self._calculate_recency(fact_dict)
        
        # Apply formula: (C × I) × AD × RB
        base_score = certainty * impact
        temporal_score = age_decay * recency_boost
        final_score = base_score * temporal_score
        
        return final_score
    
    def _calculate_certainty(self, fact: Dict[str, Any]) -> float:
        """
        Calculate certainty score (confidence in fact's accuracy).
        
        Priority:
        1. Explicit 'certainty' field (from LLM)
        2. Heuristic based on content analysis
        3. Default certainty value
        
        Args:
            fact: Fact dictionary
        
        Returns:
            float: Certainty score (0.0-1.0)
        """
        # Check for explicit certainty from LLM
        if 'certainty' in fact and fact['certainty'] is not None:
            return max(0.0, min(1.0, float(fact['certainty'])))
        
        # Apply heuristics based on content
        content = fact.get('content', '').lower()
        
        # Check for certainty indicators in content
        if any(phrase in content for phrase in ['i prefer', 'i want', 'i need', 'always', 'never']):
            return self.certainty_heuristics.get('explicit_statement', 0.9)
        elif any(phrase in content for phrase in ['usually', 'often', 'typically', 'generally']):
            return self.certainty_heuristics.get('implied_preference', 0.8)
        elif any(phrase in content for phrase in ['might', 'maybe', 'possibly', 'could']):
            return self.certainty_heuristics.get('speculation', 0.4)
        elif any(phrase in content for phrase in ['observed', 'noticed', 'seen']):
            return self.certainty_heuristics.get('observation', 0.6)
        
        # Default certainty
        return self.default_certainty
    
    def _calculate_impact(self, fact: Dict[str, Any]) -> float:
        """
        Calculate impact score (importance/relevance of fact).
        
        Based on fact_type classification. Higher weight = more important
        to remember long-term.
        
        Args:
            fact: Fact dictionary
        
        Returns:
            float: Impact score (0.0-1.0)
        """
        fact_type = fact.get('fact_type', 'mention').lower()
        
        # Look up impact weight for this fact type
        impact = self.impact_weights.get(fact_type, 0.5)
        
        # Adjust impact based on metadata
        # Boost if fact has high access count (indicates importance)
        if fact.get('access_count', 0) > 10:
            impact = min(1.0, impact * 1.1)
        
        # Boost if fact is tagged as important
        if fact.get('is_important', False):
            impact = min(1.0, impact * 1.2)
        
        return impact
    
    def _calculate_age_decay(self, fact: Dict[str, Any]) -> float:
        """
        Calculate age decay factor (older facts decay exponentially).
        
        Formula: exp(-lambda * age_days)
        
        Where:
        - lambda: decay rate (higher = faster decay)
        - age_days: days since fact creation
        
        Args:
            fact: Fact dictionary with 'created_at' timestamp
        
        Returns:
            float: Age decay factor (min_score to 1.0)
        """
        created_at = fact.get('created_at')
        
        if created_at is None:
            # No timestamp, assume it's new
            return 1.0
        
        # Ensure we have a datetime object
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        # Calculate age in days
        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        age_delta = now - created_at
        age_days = age_delta.total_seconds() / 86400  # seconds to days
        
        # Cap at max_age_days
        age_days = min(age_days, self.max_age_days)
        
        # Apply exponential decay
        decay = math.exp(-self.age_decay_lambda * age_days)
        
        # Ensure minimum score
        return max(self.min_age_score, decay)
    
    def _calculate_recency(self, fact: Dict[str, Any]) -> float:
        """
        Calculate recency boost (rewards frequently accessed facts).
        
        Formula: 1 + (boost_factor * log(1 + access_count))
        
        Logarithmic boost prevents runaway scores for heavily accessed facts.
        
        Args:
            fact: Fact dictionary with 'access_count'
        
        Returns:
            float: Recency boost (1.0 to 1.0+max_boost)
        """
        access_count = fact.get('access_count', 0)
        
        if access_count <= 0:
            return 1.0
        
        # Logarithmic boost to prevent runaway
        boost = self.recency_boost_factor * math.log(1 + access_count)
        
        # Cap at max_boost
        boost = min(boost, self.max_recency_boost)
        
        return 1.0 + boost
    
    def exceeds_threshold(self, fact: Union[Dict[str, Any], Fact]) -> bool:
        """
        Check if a fact's CIAR score exceeds the promotion threshold.
        
        Args:
            fact: Fact dictionary or Fact model
        
        Returns:
            bool: True if score >= threshold, eligible for promotion
        """
        score = self.calculate(fact)
        return score >= self.threshold
    
    def calculate_components(self, fact: Union[Dict[str, Any], Fact]) -> Dict[str, float]:
        """
        Calculate all CIAR components separately for debugging/analysis.
        
        Args:
            fact: Fact dictionary or Fact model
        
        Returns:
            dict: Component scores with keys:
                - certainty: Confidence score (0.0-1.0)
                - impact: Importance score (0.0-1.0)
                - age_decay: Time decay factor (0.1-1.0)
                - recency_boost: Access boost (1.0-1.3)
                - base_score: certainty × impact
                - temporal_score: age_decay × recency_boost
                - final_score: base_score × temporal_score
        """
        # Convert Fact model to dict if needed
        if isinstance(fact, Fact):
            fact_dict = fact.model_dump()
        else:
            fact_dict = fact
        
        certainty = self._calculate_certainty(fact_dict)
        impact = self._calculate_impact(fact_dict)
        age_decay = self._calculate_age_decay(fact_dict)
        recency_boost = self._calculate_recency(fact_dict)
        
        base_score = certainty * impact
        temporal_score = age_decay * recency_boost
        final_score = base_score * temporal_score
        
        return {
            'certainty': certainty,
            'impact': impact,
            'age_decay': age_decay,
            'recency_boost': recency_boost,
            'base_score': base_score,
            'temporal_score': temporal_score,
            'final_score': final_score
        }
