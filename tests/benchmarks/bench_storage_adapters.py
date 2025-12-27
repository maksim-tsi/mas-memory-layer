"""
Storage adapter performance benchmark runner.

Executes synthetic workloads against all storage adapters and collects
metrics for performance analysis and publication.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.storage.redis_adapter import RedisAdapter
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.typesense_adapter import TypesenseAdapter
from tests.benchmarks.workload_generator import WorkloadGenerator, WorkloadOperation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StorageBenchmark:
    """
    Run performance benchmarks on storage adapters.
    
    This benchmark:
    1. Initializes all storage adapters
    2. Generates synthetic workload
    3. Executes workload against each adapter
    4. Collects metrics using existing metrics infrastructure
    5. Saves results to JSON for analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize benchmark runner.
        
        Args:
            config: Optional configuration override
        """
        self.config = config or self._default_config()
        self.results_dir = Path(__file__).parent.parent.parent / "benchmarks" / "results" / "raw"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.adapters = {}
        self.adapter_configs = self._get_adapter_configs()
    
    def _default_config(self) -> Dict[str, Any]:
        """Get default benchmark configuration."""
        return {
            'workload_size': 10000,
            'workload_seed': 42,
            'adapters': ['redis_l1', 'redis_l2', 'qdrant', 'neo4j', 'typesense']
        }
    
    def _get_adapter_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configuration for each adapter.
        
        Loads configuration from environment variables (.env file).
        """
        # Get environment variables with fallbacks
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        stg_ip = os.getenv('STG_IP', 'localhost')
        qdrant_port = os.getenv('QDRANT_PORT', '6333')
        neo4j_bolt_port = os.getenv('NEO4J_BOLT_PORT', '7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
        typesense_port = os.getenv('TYPESENSE_PORT', '8108')
        typesense_api_key = os.getenv('TYPESENSE_API_KEY', 'xyz')
        
        return {
            'redis_l1': {
                'url': f'{redis_url}/0',
                'db': 0,
                'window_size': 10,
                'ttl_seconds': 86400,
                'metrics': {'enabled': True}
            },
            'redis_l2': {
                'url': f'{redis_url}/1',
                'db': 1,
                'window_size': 50,
                'ttl_seconds': 604800,  # 7 days
                'metrics': {'enabled': True}
            },
            'qdrant': {
                'url': f'http://{stg_ip}:{qdrant_port}',
                'collection_name': 'benchmark_memory',
                'vector_size': 384,
                'metrics': {'enabled': True}
            },
            'neo4j': {
                'uri': f'bolt://{stg_ip}:{neo4j_bolt_port}',
                'user': neo4j_user,
                'password': neo4j_password,
                'database': 'neo4j',
                'metrics': {'enabled': True}
            },
            'typesense': {
                'url': f'http://{stg_ip}:{typesense_port}',
                'api_key': typesense_api_key,
                'collection_name': 'benchmark_documents',
                'metrics': {'enabled': True}
            }
        }
    
    async def initialize_adapters(self, adapter_names: List[str]) -> None:
        """
        Initialize and connect to storage adapters.
        
        Args:
            adapter_names: List of adapter names to initialize
        """
        logger.info(f"Initializing {len(adapter_names)} adapters...")
        
        for name in adapter_names:
            try:
                if name == 'redis_l1':
                    adapter = RedisAdapter(self.adapter_configs['redis_l1'])
                elif name == 'redis_l2':
                    adapter = RedisAdapter(self.adapter_configs['redis_l2'])
                elif name == 'qdrant':
                    adapter = QdrantAdapter(self.adapter_configs['qdrant'])
                elif name == 'neo4j':
                    adapter = Neo4jAdapter(self.adapter_configs['neo4j'])
                elif name == 'typesense':
                    adapter = TypesenseAdapter(self.adapter_configs['typesense'])
                else:
                    logger.warning(f"Unknown adapter: {name}, skipping")
                    continue
                
                await adapter.connect()
                self.adapters[name] = adapter
                logger.info(f"✓ {name} connected")
                
            except Exception as e:
                logger.error(f"✗ Failed to connect {name}: {e}")
                logger.warning(f"  Skipping {name} in benchmark")
    
    async def cleanup_adapters(self) -> None:
        """Disconnect all adapters."""
        logger.info("Cleaning up adapters...")
        
        for name, adapter in self.adapters.items():
            try:
                await adapter.disconnect()
                logger.info(f"✓ {name} disconnected")
            except Exception as e:
                logger.error(f"✗ Error disconnecting {name}: {e}")
    
    async def run_benchmark(
        self,
        workload_size: Optional[int] = None,
        workload_seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run complete benchmark suite.
        
        Args:
            workload_size: Number of operations (overrides config)
            workload_seed: Random seed (overrides config)
        
        Returns:
            Complete benchmark results
        """
        size = workload_size or self.config['workload_size']
        seed = workload_seed or self.config['workload_seed']
        
        logger.info("="*80)
        logger.info("Starting Storage Adapter Benchmark")
        logger.info(f"Workload size: {size} operations")
        logger.info(f"Random seed: {seed}")
        logger.info("="*80)
        
        # Initialize adapters
        adapter_names = self.config['adapters']
        await self.initialize_adapters(adapter_names)
        
        if not self.adapters:
            logger.error("No adapters available for benchmarking!")
            return {'error': 'No adapters connected'}
        
        # Generate workload
        logger.info(f"\n📊 Generating workload ({size} operations)...")
        generator = WorkloadGenerator(seed=seed)
        workload = generator.generate_workload(size=size)
        logger.info(f"✓ Workload generated: {len(workload)} operations")
        
        # Run benchmark for each adapter
        results = {
            'benchmark_config': {
                'workload_size': size,
                'workload_seed': seed,
                'timestamp': datetime.now().isoformat(),
                'adapters': list(self.adapters.keys())
            },
            'adapters': {}
        }
        
        for name, adapter in self.adapters.items():
            logger.info(f"\n{'='*80}")
            logger.info(f"Benchmarking: {name}")
            logger.info(f"{'='*80}")
            
            try:
                adapter_results = await self._run_adapter_benchmark(
                    adapter, name, workload
                )
                results['adapters'][name] = adapter_results
                
                # Log quick summary
                logger.info(f"\n✓ {name} benchmark complete:")
                logger.info(f"  Operations: {adapter_results['total_operations']}")
                logger.info(f"  Success rate: {adapter_results['success_rate']*100:.2f}%")
                
            except Exception as e:
                logger.error(f"✗ Error benchmarking {name}: {e}")
                results['adapters'][name] = {
                    'error': str(e),
                    'status': 'failed'
                }
        
        # Cleanup
        await self.cleanup_adapters()
        
        # Save results
        output_file = self._save_results(results)
        logger.info(f"\n{'='*80}")
        logger.info("✓ Benchmark complete!")
        logger.info(f"📁 Results saved to: {output_file}")
        logger.info(f"{'='*80}")
        
        return results
    
    async def _run_adapter_benchmark(
        self,
        adapter: Any,
        adapter_name: str,
        workload: List[WorkloadOperation]
    ) -> Dict[str, Any]:
        """
        Run benchmark for a single adapter.
        
        Args:
            adapter: Storage adapter instance
            adapter_name: Name of the adapter
            workload: List of operations to execute
        
        Returns:
            Benchmark results for this adapter
        """
        # Filter workload for this adapter
        adapter_ops = [op for op in workload if op.adapter == adapter_name]
        
        logger.info(f"Executing {len(adapter_ops)} operations...")
        
        success_count = 0
        error_count = 0
        
        for i, op in enumerate(adapter_ops):
            if (i + 1) % 1000 == 0:
                logger.info(f"  Progress: {i+1}/{len(adapter_ops)} operations")
            
            try:
                await self._execute_operation(adapter, op)
                success_count += 1
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # Log first few errors only
                    logger.debug(f"  Error in {op.op_type}: {e}")
        
        # Get metrics from adapter
        metrics_json = await adapter.export_metrics('json')
        metrics = json.loads(metrics_json)
        
        # Compute summary statistics
        return {
            'total_operations': len(adapter_ops),
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': success_count / len(adapter_ops) if adapter_ops else 0,
            'metrics': metrics,
            'status': 'completed'
        }
    
    async def _execute_operation(
        self,
        adapter: Any,
        op: WorkloadOperation
    ) -> Any:
        """
        Execute a single workload operation.
        
        Args:
            adapter: Storage adapter
            op: Operation to execute
        
        Returns:
            Operation result
        """
        if op.op_type == 'store':
            return await adapter.store(op.data)
        
        elif op.op_type == 'retrieve':
            return await adapter.retrieve(op.item_id)
        
        elif op.op_type == 'search':
            return await adapter.search(op.query)
        
        elif op.op_type == 'delete':
            return await adapter.delete(op.item_id)
        
        else:
            raise ValueError(f"Unknown operation type: {op.op_type}")
    
    def _save_results(self, results: Dict[str, Any]) -> Path:
        """
        Save benchmark results to JSON file.
        
        Args:
            results: Benchmark results dictionary
        
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_{timestamp}.json"
        output_file = self.results_dir / filename
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        return output_file


async def main():
    """Main entry point for benchmark script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run storage adapter performance benchmarks'
    )
    parser.add_argument(
        '--size',
        type=int,
        default=10000,
        help='Workload size (number of operations, default: 10000)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    parser.add_argument(
        '--adapters',
        nargs='+',
        choices=['redis_l1', 'redis_l2', 'qdrant', 'neo4j', 'typesense'],
        default=['redis_l1', 'redis_l2', 'qdrant', 'neo4j', 'typesense'],
        help='Adapters to benchmark (default: all)'
    )
    
    args = parser.parse_args()
    
    config = {
        'workload_size': args.size,
        'workload_seed': args.seed,
        'adapters': args.adapters
    }
    
    benchmark = StorageBenchmark(config)
    await benchmark.run_benchmark()


if __name__ == "__main__":
    asyncio.run(main())
