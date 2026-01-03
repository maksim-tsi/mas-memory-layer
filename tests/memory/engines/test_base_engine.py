import pytest
from typing import Dict, Any
from src.memory.engines.base_engine import BaseEngine

class ConcreteEngine(BaseEngine):
    async def process(self) -> Dict[str, Any]:
        return {"status": "processed"}
    
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy"}

@pytest.mark.asyncio
async def test_base_engine_initialization():
    engine = ConcreteEngine()
    assert engine.metrics is not None
    assert engine._is_running is False

@pytest.mark.asyncio
async def test_base_engine_methods():
    engine = ConcreteEngine()
    process_result = await engine.process()
    assert process_result == {"status": "processed"}
    
    health_result = await engine.health_check()
    assert health_result == {"status": "healthy"}
    
    metrics = await engine.get_metrics()
    assert isinstance(metrics, dict)
