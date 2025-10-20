#!/usr/bin/env python3
"""
Convenience script to run storage adapter benchmarks.

This script provides a simple interface to run benchmarks and analyze results.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.benchmarks.bench_storage_adapters import main as run_benchmark
from tests.benchmarks.results_analyzer import main as analyze_results


def print_banner():
    """Print benchmark suite banner."""
    print("=" * 80)
    print(" MAS Memory Layer - Storage Adapter Performance Benchmark")
    print("=" * 80)
    print()


def print_usage():
    """Print usage information."""
    print("Usage:")
    print("  python scripts/run_storage_benchmark.py [command] [options]")
    print()
    print("Commands:")
    print("  run      - Run benchmark suite (default)")
    print("  analyze  - Analyze benchmark results")
    print("  help     - Show this help message")
    print()
    print("Run Options:")
    print("  --size N           - Workload size (default: 10000)")
    print("  --seed N           - Random seed (default: 42)")
    print("  --adapters A B C   - Adapters to benchmark (default: all)")
    print()
    print("Analyze Options:")
    print("  --results FILE     - Results file to analyze (default: most recent)")
    print("  --output DIR       - Output directory (default: benchmarks/reports/tables)")
    print()
    print("Examples:")
    print("  # Run default benchmark (10K ops)")
    print("  python scripts/run_storage_benchmark.py")
    print()
    print("  # Run small benchmark (1K ops)")
    print("  python scripts/run_storage_benchmark.py run --size 1000")
    print()
    print("  # Benchmark only Redis adapters")
    print("  python scripts/run_storage_benchmark.py run --adapters redis_l1 redis_l2")
    print()
    print("  # Analyze most recent results")
    print("  python scripts/run_storage_benchmark.py analyze")
    print()


async def main():
    """Main entry point."""
    print_banner()
    
    if len(sys.argv) < 2:
        # Default to run
        await run_benchmark()
        return
    
    command = sys.argv[1]
    
    if command == "help" or command == "--help" or command == "-h":
        print_usage()
    
    elif command == "run":
        # Remove 'run' from argv so argparse in run_benchmark works correctly
        sys.argv.pop(1)
        await run_benchmark()
    
    elif command == "analyze":
        # Remove 'analyze' from argv
        sys.argv.pop(1)
        analyze_results()
    
    elif command.startswith("--"):
        # Assume it's a flag for run command
        await run_benchmark()
    
    else:
        print(f"Unknown command: {command}")
        print()
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
