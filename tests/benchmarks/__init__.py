"""
Storage adapter benchmarking suite.

This module provides tools for benchmarking the performance of storage adapters
in the MAS Memory Layer system.

Components:
- workload_generator: Generate synthetic workloads
- bench_storage_adapters: Execute benchmarks
- results_analyzer: Analyze and present results
"""

__version__ = "1.0.0"

from .workload_generator import WorkloadGenerator, WorkloadOperation, create_workload_config
from .bench_storage_adapters import StorageBenchmark
from .results_analyzer import BenchmarkAnalyzer

__all__ = [
    'WorkloadGenerator',
    'WorkloadOperation',
    'create_workload_config',
    'StorageBenchmark',
    'BenchmarkAnalyzer',
]
