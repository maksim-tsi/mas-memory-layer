"""
Unit Tests for CIAR Tools.

Tests the CIAR calculation, filtering, and explanation tools with mocked
CIARScorer dependency.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

from src.agents.tools.ciar_tools import (
    ciar_calculate,
    ciar_filter,
    ciar_explain,
    CIARCalculateInput,
    CIARFilterInput,
    CIARExplainInput
)


class TestCIARToolInputSchemas:
    """Test Pydantic input schemas for CIAR tools."""
    
    def test_ciar_calculate_input_schema_valid(self):
        """Test valid CIARCalculateInput."""
        data = {
            'content': 'Container MAEU1234567 arrived',
            'certainty': 0.9,
            'impact': 0.8,
            'fact_type': 'event',
            'days_old': 0,
            'access_count': 0
        }
        schema = CIARCalculateInput(**data)
        assert schema.content == 'Container MAEU1234567 arrived'
        assert schema.certainty == 0.9
        assert schema.impact == 0.8
    
    def test_ciar_calculate_input_schema_defaults(self):
        """Test default values in CIARCalculateInput."""
        data = {
            'content': 'Test',
            'certainty': 0.8,
            'impact': 0.7
        }
        schema = CIARCalculateInput(**data)
        assert schema.fact_type == 'observation'
        assert schema.days_old == 0
        assert schema.access_count == 0
    
    def test_ciar_calculate_input_schema_validation(self):
        """Test validation in CIARCalculateInput."""
        # Certainty out of range
        with pytest.raises(ValueError):
            CIARCalculateInput(content='Test', certainty=1.5, impact=0.8)
        
        # Negative days_old
        with pytest.raises(ValueError):
            CIARCalculateInput(content='Test', certainty=0.8, impact=0.7, days_old=-1)
    
    def test_ciar_filter_input_schema(self):
        """Test CIARFilterInput schema."""
        facts = [
            {'content': 'Fact 1', 'certainty': 0.9, 'impact': 0.8},
            {'content': 'Fact 2', 'certainty': 0.5, 'impact': 0.4}
        ]
        schema = CIARFilterInput(facts=facts, min_threshold=0.6)
        assert len(schema.facts) == 2
        assert schema.min_threshold == 0.6
        assert schema.return_scores is True


class TestCIARToolMetadata:
    """Test tool metadata (name, description, args_schema)."""
    
    def test_ciar_calculate_metadata(self):
        """Test ciar_calculate tool metadata."""
        assert ciar_calculate.name == 'ciar_calculate'
        assert 'Calculate CIAR score' in ciar_calculate.description
        assert ciar_calculate.args_schema == CIARCalculateInput
    
    def test_ciar_filter_metadata(self):
        """Test ciar_filter tool metadata."""
        assert ciar_filter.name == 'ciar_filter'
        assert 'Batch filter facts' in ciar_filter.description
        assert ciar_filter.args_schema == CIARFilterInput
    
    def test_ciar_explain_metadata(self):
        """Test ciar_explain tool metadata."""
        assert ciar_explain.name == 'ciar_explain'
        assert 'human-readable explanation' in ciar_explain.description
        assert ciar_explain.args_schema == CIARExplainInput


class TestCIARCalculateTool:
    """Test ciar_calculate tool functionality."""
    
    @pytest.mark.asyncio
    async def test_ciar_calculate_high_score(self):
        """Test CIAR calculation for high-scoring fact."""
        # Mock runtime
        mock_runtime = Mock()
        mock_runtime.stream_status = AsyncMock()
        
        result = await ciar_calculate.coroutine(
            content="Critical: Port closure announced",
            certainty=0.95,
            impact=0.90,
            fact_type="event",
            days_old=0,
            access_count=0,
            runtime=mock_runtime
        )
        
        # Parse JSON result
        data = json.loads(result)
        assert data['is_promotable'] is True
        assert data['final_score'] > 0.6
        assert '✅' in data['verdict']
        assert 'PROMOTE to L2' in data['verdict']
    
    @pytest.mark.asyncio
    async def test_ciar_calculate_low_score(self):
        """Test CIAR calculation for low-scoring fact."""
        mock_runtime = Mock()
        mock_runtime.stream_status = AsyncMock()
        
        result = await ciar_calculate.coroutine(
            content="Minor: Status check",
            certainty=0.4,
            impact=0.3,
            fact_type="observation",
            days_old=0,
            access_count=0,
            runtime=mock_runtime
        )
        
        data = json.loads(result)
        assert data['is_promotable'] is False
        assert data['final_score'] < 0.6
        assert '❌' in data['verdict']
        assert 'REJECT' in data['verdict']
    
    @pytest.mark.asyncio
    async def test_ciar_calculate_with_age_decay(self):
        """Test CIAR calculation with age decay applied."""
        mock_runtime = Mock()
        mock_runtime.stream_status = AsyncMock()
        
        result = await ciar_calculate.coroutine(
            content="Old event",
            certainty=0.9,
            impact=0.8,
            days_old=30,  # 30 days old
            access_count=0,
            runtime=mock_runtime
        )
        
        data = json.loads(result)
        # Age decay should reduce score
        assert data['components']['age_decay'] < 1.0
        assert data['final_score'] < (0.9 * 0.8)  # Base score without decay
    
    @pytest.mark.asyncio
    async def test_ciar_calculate_with_recency_boost(self):
        """Test CIAR calculation with recency boost."""
        mock_runtime = Mock()
        mock_runtime.stream_status = AsyncMock()
        
        result = await ciar_calculate.coroutine(
            content="Frequently accessed fact",
            certainty=0.8,
            impact=0.7,
            days_old=0,
            access_count=10,  # Accessed 10 times
            runtime=mock_runtime
        )
        
        data = json.loads(result)
        # Recency boost should increase score
        assert data['components']['recency_boost'] > 1.0
        assert data['final_score'] > (0.8 * 0.7)  # Base score without boost


class TestCIARFilterTool:
    """Test ciar_filter tool functionality."""
    
    @pytest.mark.asyncio
    async def test_ciar_filter_mixed_scores(self):
        """Test filtering with mixed high/low CIAR scores."""
        mock_runtime = Mock()
        mock_runtime.stream_status = AsyncMock()
        
        now = datetime.now(timezone.utc)
        facts = [
            {'content': 'High fact 1', 'certainty': 0.9, 'impact': 0.8, 'created_at': now.isoformat(), 'access_count': 0},
            {'content': 'Low fact', 'certainty': 0.3, 'impact': 0.2, 'created_at': now.isoformat(), 'access_count': 0},
            {'content': 'High fact 2', 'certainty': 0.85, 'impact': 0.75, 'created_at': now.isoformat(), 'access_count': 0},
        ]
        
        result = await ciar_filter.coroutine(
            facts=facts,
            min_threshold=0.6,
            return_scores=True,
            runtime=mock_runtime
        )
        
        data = json.loads(result)
        assert data['input_count'] == 3
        assert data['filtered_count'] == 2  # Only high-scoring facts
        assert data['threshold'] == 0.6
        assert len(data['facts']) == 2
        # Verify scores returned
        for fact in data['facts']:
            assert 'ciar_score' in fact
            assert fact['ciar_score'] >= 0.6
    
    @pytest.mark.asyncio
    async def test_ciar_filter_all_pass(self):
        """Test filtering where all facts pass threshold."""
        mock_runtime = Mock()
        mock_runtime.stream_status = AsyncMock()
        
        now = datetime.now(timezone.utc)
        facts = [
            {'content': f'High fact {i}', 'certainty': 0.9, 'impact': 0.8, 'created_at': now.isoformat(), 'access_count': 0}
            for i in range(5)
        ]
        
        result = await ciar_filter.coroutine(
            facts=facts,
            min_threshold=0.5,
            return_scores=True,
            runtime=mock_runtime
        )
        
        data = json.loads(result)
        assert data['filtered_count'] == 5
        assert data['pass_rate'] == 100.0


class TestCIARExplainTool:
    """Test ciar_explain tool functionality."""
    
    @pytest.mark.asyncio
    async def test_ciar_explain_breakdown(self):
        """Test CIAR score explanation with component breakdown."""
        mock_runtime = Mock()
        
        result = await ciar_explain.coroutine(
            content="Container MAEU1234567 departed from Port of LA",
            certainty=0.9,
            impact=0.85,
            fact_type="event",
            days_old=5,
            access_count=3,
            runtime=mock_runtime
        )
        
        # Verify explanation contains all components
        assert 'Certainty (C):' in result
        assert 'Impact (I):' in result
        assert 'Age Decay (AD):' in result
        assert 'Recency Boost (RB):' in result
        assert 'Base Score' in result
        assert 'Temporal Score' in result
        assert 'Final CIAR Score' in result
        assert 'Verdict:' in result
    
    @pytest.mark.asyncio
    async def test_ciar_explain_promotable_verdict(self):
        """Test explanation shows promotable verdict for high score."""
        mock_runtime = Mock()
        
        result = await ciar_explain.coroutine(
            content="High priority event",
            certainty=0.95,
            impact=0.90,
            fact_type="event",
            days_old=0,
            access_count=0,
            runtime=mock_runtime
        )
        
        assert '✅ PROMOTE to L2 Working Memory' in result
    
    @pytest.mark.asyncio
    async def test_ciar_explain_reject_verdict(self):
        """Test explanation shows reject verdict for low score."""
        mock_runtime = Mock()
        
        result = await ciar_explain.coroutine(
            content="Low priority observation",
            certainty=0.4,
            impact=0.3,
            fact_type="observation",
            days_old=0,
            access_count=0,
            runtime=mock_runtime
        )
        
        assert '❌ REJECT' in result
        assert 'Needs +' in result  # Shows margin needed
