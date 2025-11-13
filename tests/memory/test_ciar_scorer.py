"""
Tests for CIAR Scoring System

Tests the Certainty-Impact-Age-Recency (CIAR) scoring algorithm
used to determine fact promotion from L1 to L2.

Author: MAS Memory Layer Team
Date: November 2025
"""

import pytest
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, mock_open

from src.memory.ciar_scorer import CIARScorer
from src.memory.models import Fact


class TestCIARScorerInitialization:
    """Test scorer initialization and configuration loading."""
    
    def test_init_with_default_config(self):
        """Should load default config from config/ciar_config.yaml"""
        scorer = CIARScorer()
        
        assert scorer.threshold == 0.6
        assert scorer.age_decay_lambda == 0.1
        assert scorer.recency_boost_factor == 0.05
        assert scorer.default_certainty == 0.7
        assert 'preference' in scorer.impact_weights
        assert scorer.impact_weights['preference'] == 0.9
    
    def test_init_with_custom_config(self, tmp_path):
        """Should load custom config from specified path"""
        config_content = """
ciar:
  threshold: 0.8
  age_decay:
    lambda: 0.2
    max_age_days: 60
    min_score: 0.05
  recency:
    boost_factor: 0.1
    max_boost: 0.5
  certainty:
    default: 0.6
  impact_weights:
    preference: 0.95
    mention: 0.2
  formula:
    certainty_weight: 1.0
    impact_weight: 1.0
    temporal_weight: 1.0
"""
        config_path = tmp_path / "test_ciar_config.yaml"
        config_path.write_text(config_content)
        
        scorer = CIARScorer(config_path=str(config_path))
        
        assert scorer.threshold == 0.8
        assert scorer.age_decay_lambda == 0.2
        assert scorer.max_age_days == 60
        assert scorer.recency_boost_factor == 0.1
        assert scorer.default_certainty == 0.6


class TestCIARScorerCertainty:
    """Test certainty score calculation."""
    
    @pytest.fixture
    def scorer(self):
        return CIARScorer()
    
    def test_explicit_certainty_from_field(self, scorer):
        """Should use explicit certainty value if provided"""
        fact = {'content': 'Test fact', 'certainty': 0.95}
        certainty = scorer._calculate_certainty(fact)
        assert certainty == 0.95
    
    def test_certainty_clamped_to_range(self, scorer):
        """Should clamp certainty to [0.0, 1.0]"""
        fact_high = {'content': 'Test', 'certainty': 1.5}
        fact_low = {'content': 'Test', 'certainty': -0.3}
        
        assert scorer._calculate_certainty(fact_high) == 1.0
        assert scorer._calculate_certainty(fact_low) == 0.0
    
    def test_heuristic_explicit_statement(self, scorer):
        """Should recognize explicit statements (I prefer, I want, etc.)"""
        fact = {'content': 'I prefer morning meetings'}
        certainty = scorer._calculate_certainty(fact)
        assert certainty == 1.0  # explicit_statement
    
    def test_heuristic_implied_preference(self, scorer):
        """Should recognize implied preferences (usually, often, etc.)"""
        fact = {'content': 'I usually work from home'}
        certainty = scorer._calculate_certainty(fact)
        assert certainty == 0.8  # implied_preference
    
    def test_heuristic_speculation(self, scorer):
        """Should recognize speculation (might, maybe, etc.)"""
        fact = {'content': 'I might be interested in that'}
        certainty = scorer._calculate_certainty(fact)
        assert certainty == 0.4  # speculation
    
    def test_heuristic_observation(self, scorer):
        """Should recognize observations"""
        fact = {'content': 'User observed using keyboard shortcuts'}
        certainty = scorer._calculate_certainty(fact)
        assert certainty == 0.6  # observation
    
    def test_default_certainty(self, scorer):
        """Should return default certainty if no heuristics match"""
        fact = {'content': 'Some neutral statement'}
        certainty = scorer._calculate_certainty(fact)
        assert certainty == 0.7  # default


class TestCIARScorerImpact:
    """Test impact score calculation."""
    
    @pytest.fixture
    def scorer(self):
        return CIARScorer()
    
    def test_impact_by_fact_type_preference(self, scorer):
        """Should assign high impact to preferences"""
        fact = {'fact_type': 'preference'}
        impact = scorer._calculate_impact(fact)
        assert impact == 0.9
    
    def test_impact_by_fact_type_constraint(self, scorer):
        """Should assign high impact to constraints"""
        fact = {'fact_type': 'constraint'}
        impact = scorer._calculate_impact(fact)
        assert impact == 0.8
    
    def test_impact_by_fact_type_entity(self, scorer):
        """Should assign moderate impact to entities"""
        fact = {'fact_type': 'entity'}
        impact = scorer._calculate_impact(fact)
        assert impact == 0.6
    
    def test_impact_by_fact_type_mention(self, scorer):
        """Should assign low impact to mentions"""
        fact = {'fact_type': 'mention'}
        impact = scorer._calculate_impact(fact)
        assert impact == 0.3
    
    def test_impact_default_for_unknown_type(self, scorer):
        """Should use default impact for unknown fact types"""
        fact = {'fact_type': 'unknown_type'}
        impact = scorer._calculate_impact(fact)
        assert impact == 0.5
    
    def test_impact_boost_for_high_access_count(self, scorer):
        """Should boost impact for frequently accessed facts"""
        fact = {'fact_type': 'entity', 'access_count': 15}
        impact = scorer._calculate_impact(fact)
        assert impact > 0.6  # Base entity impact with boost
        assert impact <= 1.0
    
    def test_impact_boost_for_important_flag(self, scorer):
        """Should boost impact for facts marked as important"""
        fact = {'fact_type': 'entity', 'is_important': True}
        impact = scorer._calculate_impact(fact)
        assert impact > 0.6  # Base entity impact with boost
        assert impact <= 1.0


class TestCIARScorerAgeDecay:
    """Test age decay calculation."""
    
    @pytest.fixture
    def scorer(self):
        return CIARScorer()
    
    def test_age_decay_new_fact(self, scorer):
        """Should return 1.0 for brand new facts"""
        now = datetime.now(timezone.utc)
        fact = {'created_at': now}
        decay = scorer._calculate_age_decay(fact)
        assert decay == pytest.approx(1.0, rel=0.01)
    
    def test_age_decay_no_timestamp(self, scorer):
        """Should return 1.0 if no timestamp provided"""
        fact = {}
        decay = scorer._calculate_age_decay(fact)
        assert decay == 1.0
    
    def test_age_decay_one_day_old(self, scorer):
        """Should decay exponentially for 1-day-old fact"""
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        fact = {'created_at': one_day_ago}
        decay = scorer._calculate_age_decay(fact)
        
        expected = math.exp(-0.1 * 1)  # lambda=0.1, age=1
        assert decay == pytest.approx(expected, rel=0.01)
        assert 0.9 < decay < 0.91
    
    def test_age_decay_one_week_old(self, scorer):
        """Should decay significantly for 7-day-old fact"""
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        fact = {'created_at': one_week_ago}
        decay = scorer._calculate_age_decay(fact)
        
        expected = math.exp(-0.1 * 7)  # lambda=0.1, age=7
        assert decay == pytest.approx(expected, rel=0.01)
        assert 0.49 < decay < 0.51
    
    def test_age_decay_very_old_fact(self, scorer):
        """Should apply minimum score for very old facts"""
        very_old = datetime.now(timezone.utc) - timedelta(days=100)
        fact = {'created_at': very_old}
        decay = scorer._calculate_age_decay(fact)
        
        # Should be capped at min_score (0.1)
        assert decay >= 0.1
        assert decay < 0.2
    
    def test_age_decay_with_string_timestamp(self, scorer):
        """Should handle ISO format string timestamps"""
        timestamp_str = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        fact = {'created_at': timestamp_str}
        decay = scorer._calculate_age_decay(fact)
        
        assert 0.9 < decay < 0.91


class TestCIARScorerRecency:
    """Test recency boost calculation."""
    
    @pytest.fixture
    def scorer(self):
        return CIARScorer()
    
    def test_recency_no_access(self, scorer):
        """Should return 1.0 for facts with no access"""
        fact = {'access_count': 0}
        boost = scorer._calculate_recency(fact)
        assert boost == 1.0
    
    def test_recency_missing_access_count(self, scorer):
        """Should return 1.0 if access_count missing"""
        fact = {}
        boost = scorer._calculate_recency(fact)
        assert boost == 1.0
    
    def test_recency_low_access(self, scorer):
        """Should apply small boost for low access count"""
        fact = {'access_count': 5}
        boost = scorer._calculate_recency(fact)
        
        expected = 1.0 + (0.05 * math.log(6))  # boost_factor * log(1+5)
        assert boost == pytest.approx(expected, rel=0.01)
        assert boost > 1.0
        assert boost < 1.1
    
    def test_recency_high_access(self, scorer):
        """Should apply larger boost for high access count"""
        fact = {'access_count': 50}
        boost = scorer._calculate_recency(fact)
        
        expected = 1.0 + (0.05 * math.log(51))  # boost_factor * log(1+50)
        assert boost == pytest.approx(expected, rel=0.01)
        assert boost > 1.1
    
    def test_recency_capped_at_max_boost(self, scorer):
        """Should cap recency boost at max_boost (1.3)"""
        fact = {'access_count': 10000}
        boost = scorer._calculate_recency(fact)
        
        assert boost <= 1.3
        assert boost == 1.3  # Should hit the cap


class TestCIARScorerCalculate:
    """Test complete CIAR score calculation."""
    
    @pytest.fixture
    def scorer(self):
        return CIARScorer()
    
    def test_calculate_new_preference_fact(self, scorer):
        """Should calculate high score for new preference fact"""
        fact = {
            'content': 'I prefer morning meetings',
            'fact_type': 'preference',
            'certainty': 0.9,
            'created_at': datetime.now(timezone.utc),
            'access_count': 0
        }
        score = scorer.calculate(fact)
        
        # High certainty (0.9) × high impact (0.9) × no decay (1.0) × no boost (1.0)
        expected = 0.9 * 0.9 * 1.0 * 1.0
        assert score == pytest.approx(expected, rel=0.01)
        assert score > 0.8
    
    def test_calculate_old_mention_fact(self, scorer):
        """Should calculate low score for old mention fact"""
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        fact = {
            'content': 'User mentioned Python',
            'fact_type': 'mention',
            'certainty': 0.6,
            'created_at': one_week_ago,
            'access_count': 0
        }
        score = scorer.calculate(fact)
        
        # Low certainty (0.6) × low impact (0.3) × decay (~0.5) × no boost (1.0)
        assert score < 0.15
    
    def test_calculate_with_recency_boost(self, scorer):
        """Should boost score for frequently accessed facts"""
        fact = {
            'content': 'Important fact',
            'fact_type': 'entity',
            'certainty': 0.8,
            'created_at': datetime.now(timezone.utc),
            'access_count': 20
        }
        score = scorer.calculate(fact)
        
        # Should be higher due to recency boost
        base_score = 0.8 * 0.6 * 1.0 * 1.0
        assert score > base_score
    
    def test_calculate_with_fact_model(self, scorer):
        """Should accept Fact model instance"""
        fact = Fact(
            fact_id='fact_123',
            content='Test fact',
            fact_type='preference',
            session_id='session_1',
            certainty=0.85,
            created_at=datetime.now(timezone.utc),
            access_count=5
        )
        score = scorer.calculate(fact)
        
        assert isinstance(score, float)
        assert score > 0.0
    
    def test_calculate_formula_structure(self, scorer):
        """Should apply formula: (C × I) × AD × RB"""
        fact = {
            'content': 'Test',
            'fact_type': 'preference',
            'certainty': 0.8,
            'created_at': datetime.now(timezone.utc) - timedelta(days=1),
            'access_count': 10
        }
        
        components = scorer.calculate_components(fact)
        
        # Verify formula structure
        expected_base = components['certainty'] * components['impact']
        expected_temporal = components['age_decay'] * components['recency_boost']
        expected_final = expected_base * expected_temporal
        
        assert components['base_score'] == pytest.approx(expected_base, rel=0.01)
        assert components['temporal_score'] == pytest.approx(expected_temporal, rel=0.01)
        assert components['final_score'] == pytest.approx(expected_final, rel=0.01)


class TestCIARScorerThreshold:
    """Test threshold checking."""
    
    @pytest.fixture
    def scorer(self):
        return CIARScorer()
    
    def test_exceeds_threshold_true(self, scorer):
        """Should return True for facts exceeding threshold"""
        fact = {
            'content': 'I prefer morning meetings',
            'fact_type': 'preference',
            'certainty': 0.9,
            'created_at': datetime.now(timezone.utc),
            'access_count': 0
        }
        assert scorer.exceeds_threshold(fact) is True
    
    def test_exceeds_threshold_false(self, scorer):
        """Should return False for facts below threshold"""
        old_fact = datetime.now(timezone.utc) - timedelta(days=10)
        fact = {
            'content': 'Mentioned something',
            'fact_type': 'mention',
            'certainty': 0.5,
            'created_at': old_fact,
            'access_count': 0
        }
        assert scorer.exceeds_threshold(fact) is False
    
    def test_exceeds_threshold_at_boundary(self, scorer):
        """Should handle facts at threshold boundary"""
        # Manually craft fact to hit threshold exactly
        fact = {
            'fact_type': 'entity',
            'certainty': 1.0,
            'created_at': datetime.now(timezone.utc),
            'access_count': 0
        }
        score = scorer.calculate(fact)
        
        # Adjust to hit threshold
        if score < scorer.threshold:
            assert scorer.exceeds_threshold(fact) is False
        else:
            assert scorer.exceeds_threshold(fact) is True


class TestCIARScorerComponents:
    """Test component breakdown functionality."""
    
    @pytest.fixture
    def scorer(self):
        return CIARScorer()
    
    def test_calculate_components_returns_all_parts(self, scorer):
        """Should return all component scores"""
        fact = {
            'content': 'Test fact',
            'fact_type': 'preference',
            'certainty': 0.8,
            'created_at': datetime.now(timezone.utc),
            'access_count': 5
        }
        components = scorer.calculate_components(fact)
        
        required_keys = [
            'certainty', 'impact', 'age_decay', 'recency_boost',
            'base_score', 'temporal_score', 'final_score'
        ]
        
        for key in required_keys:
            assert key in components
            assert isinstance(components[key], float)
    
    def test_calculate_components_matches_calculate(self, scorer):
        """Should match calculate() result in final_score"""
        fact = {
            'content': 'Test',
            'fact_type': 'entity',
            'certainty': 0.75,
            'created_at': datetime.now(timezone.utc) - timedelta(days=2),
            'access_count': 8
        }
        
        score = scorer.calculate(fact)
        components = scorer.calculate_components(fact)
        
        assert components['final_score'] == pytest.approx(score, rel=0.01)
    
    def test_calculate_components_with_fact_model(self, scorer):
        """Should work with Fact model instance"""
        fact = Fact(
            fact_id='fact_456',
            content='Model test',
            fact_type='constraint',
            session_id='session_1',
            certainty=0.9,
            created_at=datetime.now(timezone.utc),
            access_count=3
        )
        
        components = scorer.calculate_components(fact)
        
        assert 'final_score' in components
        assert components['certainty'] == 0.9
        assert components['impact'] == 0.8  # constraint weight


class TestCIARScorerEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def scorer(self):
        return CIARScorer()
    
    def test_minimal_fact_dict(self, scorer):
        """Should handle minimal fact with only required fields"""
        fact = {'content': 'Minimal fact'}
        score = scorer.calculate(fact)
        
        assert isinstance(score, float)
        assert score >= 0.0
    
    def test_empty_fact_dict(self, scorer):
        """Should handle empty fact dict with defaults"""
        fact = {}
        score = scorer.calculate(fact)
        
        assert isinstance(score, float)
        assert score >= 0.0
    
    def test_negative_access_count(self, scorer):
        """Should handle negative access count gracefully"""
        fact = {'access_count': -5}
        boost = scorer._calculate_recency(fact)
        
        assert boost == 1.0  # Should treat as no access
    
    def test_future_timestamp(self, scorer):
        """Should handle future timestamps"""
        future = datetime.now(timezone.utc) + timedelta(days=1)
        fact = {'created_at': future}
        decay = scorer._calculate_age_decay(fact)
        
        # Negative age should be handled
        assert decay >= 0.0
        assert decay <= 1.0
    
    def test_case_insensitive_fact_type(self, scorer):
        """Should handle fact_type case insensitively"""
        fact_upper = {'fact_type': 'PREFERENCE'}
        fact_lower = {'fact_type': 'preference'}
        fact_mixed = {'fact_type': 'Preference'}
        
        impact_upper = scorer._calculate_impact(fact_upper)
        impact_lower = scorer._calculate_impact(fact_lower)
        impact_mixed = scorer._calculate_impact(fact_mixed)
        
        assert impact_upper == impact_lower == impact_mixed
