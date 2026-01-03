"""
Benchmark results analyzer and publication table generator.

Analyzes benchmark results and generates publication-ready tables
for performance and reliability metrics.
"""

import json
import statistics
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class BenchmarkAnalyzer:
    """
    Analyze benchmark results and generate publication-ready tables.
    
    Generates:
    1. Latency & Throughput Performance Table
    2. Reliability & Error Handling Table
    """
    
    def __init__(self, results_file: Optional[Path] = None):
        """
        Initialize analyzer.
        
        Args:
            results_file: Path to benchmark results JSON file.
                         If None, will use most recent file.
        """
        if results_file is None:
            results_file = self._find_latest_results()
        
        self.results_file = results_file
        self.results = self._load_results()
    
    def _find_latest_results(self) -> Path:
        """Find most recent benchmark results file."""
        results_dir = Path(__file__).parent.parent.parent / "benchmarks" / "results" / "raw"
        
        if not results_dir.exists():
            raise FileNotFoundError(f"Results directory not found: {results_dir}")
        
        results_files = sorted(results_dir.glob("benchmark_*.json"))
        
        if not results_files:
            raise FileNotFoundError(f"No benchmark results found in {results_dir}")
        
        return results_files[-1]
    
    def _load_results(self) -> Dict[str, Any]:
        """Load benchmark results from JSON file."""
        with open(self.results_file) as f:
            return json.load(f)
    
    def generate_all_tables(self, output_dir: Optional[Path] = None) -> None:
        """
        Generate all publication tables.
        
        Args:
            output_dir: Directory to save tables (default: benchmarks/reports/tables)
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / "benchmarks" / "reports" / "tables"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("\n" + "="*80)
        print("Benchmark Results Analysis")
        print("="*80)
        print(f"Results file: {self.results_file.name}")
        print(f"Timestamp: {self.results['benchmark_config']['timestamp']}")
        print(f"Workload size: {self.results['benchmark_config']['workload_size']} operations")
        print("="*80)
        
        # Generate tables
        table1 = self.generate_latency_table()
        table2 = self.generate_reliability_table()
        
        # Save to files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        table1_file = output_dir / f"latency_throughput_{timestamp}.md"
        with open(table1_file, 'w') as f:
            f.write(table1)
        print(f"\n✓ Latency table saved to: {table1_file}")
        
        table2_file = output_dir / f"reliability_{timestamp}.md"
        with open(table2_file, 'w') as f:
            f.write(table2)
        print(f"✓ Reliability table saved to: {table2_file}")
        
        # Also save summary JSON
        summary = self.generate_summary()
        summary_file = output_dir.parent.parent / "results" / "processed" / f"summary_{timestamp}.json"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Summary JSON saved to: {summary_file}")
    
    def generate_latency_table(self) -> str:
        """
        Generate Table 1: Latency & Throughput Performance.
        
        Returns:
            Markdown-formatted table
        """
        print("\n" + "="*80)
        print("Table 1: Latency & Throughput Performance")
        print("="*80)
        
        # Table header
        table = "# Table 1: Latency & Throughput Performance\n\n"
        table += "| Storage Adapter | Role | Avg Latency (ms) | P95 Latency (ms) | Throughput (ops/sec) |\n"
        table += "|-----------------|------|------------------|------------------|---------------------|\n"
        
        # Adapter roles
        adapter_roles = {
            'redis_l1': 'L1 Cache (Hot)',
            'redis_l2': 'L2 Cache (Warm)',
            'qdrant': 'L3 Semantic Search',
            'neo4j': 'L3 Graph Traversal',
            'typesense': 'L3 Full-Text Search'
        }
        
        rows = []
        
        for adapter_name in ['redis_l1', 'redis_l2', 'qdrant', 'neo4j', 'typesense']:
            if adapter_name not in self.results['adapters']:
                continue
            
            adapter_data = self.results['adapters'][adapter_name]
            
            if adapter_data.get('status') == 'failed':
                row = f"| {adapter_name:<15} | {adapter_roles[adapter_name]:<20} | ERROR | ERROR | ERROR |"
                rows.append(row)
                print(row)
                continue
            
            # Extract metrics
            metrics = adapter_data['metrics']
            stats = self._compute_latency_stats(metrics)
            
            # Format row
            row = (
                f"| {adapter_name:<15} | "
                f"{adapter_roles[adapter_name]:<20} | "
                f"{stats['avg_latency']:>15.2f} | "
                f"{stats['p95_latency']:>16.2f} | "
                f"{stats['throughput']:>19.0f} |"
            )
            
            rows.append(row)
            print(row)
        
        table += "\n".join(rows) + "\n"
        
        return table
    
    def generate_reliability_table(self) -> str:
        """
        Generate Table 2: Reliability & Error Handling.
        
        Returns:
            Markdown-formatted table
        """
        print("\n" + "="*80)
        print("Table 2: Reliability & Error Handling")
        print("="*80)
        
        # Table header
        table = "# Table 2: Reliability & Error Handling\n\n"
        table += "| Storage Adapter | Success Rate | Error Rate | Total Operations | Notes |\n"
        table += "|-----------------|--------------|------------|------------------|-------|\n"
        
        rows = []
        
        for adapter_name in ['redis_l1', 'redis_l2', 'qdrant', 'neo4j', 'typesense']:
            if adapter_name not in self.results['adapters']:
                continue
            
            adapter_data = self.results['adapters'][adapter_name]
            
            if adapter_data.get('status') == 'failed':
                row = f"| {adapter_name:<15} | ERROR | ERROR | N/A | Connection failed |"
                rows.append(row)
                print(row)
                continue
            
            success_rate = adapter_data['success_rate'] * 100
            error_rate = (1 - adapter_data['success_rate']) * 100
            total_ops = adapter_data['total_operations']
            
            # Determine status
            if success_rate >= 99.9:
                notes = "Production-ready ✅"
            elif success_rate >= 99.0:
                notes = "Good"
            elif success_rate >= 95.0:
                notes = "Acceptable"
            else:
                notes = "Needs investigation ⚠️"
            
            row = (
                f"| {adapter_name:<15} | "
                f"{success_rate:>11.2f}% | "
                f"{error_rate:>9.2f}% | "
                f"{total_ops:>16,} | "
                f"{notes:<25} |"
            )
            
            rows.append(row)
            print(row)
        
        table += "\n".join(rows) + "\n"
        
        return table
    
    def generate_summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics for all adapters.
        
        Returns:
            Summary dictionary
        """
        summary = {
            'benchmark_info': self.results['benchmark_config'],
            'adapters': {}
        }
        
        for adapter_name, adapter_data in self.results['adapters'].items():
            if adapter_data.get('status') == 'failed':
                summary['adapters'][adapter_name] = {
                    'status': 'failed',
                    'error': adapter_data.get('error', 'Unknown error')
                }
                continue
            
            metrics = adapter_data['metrics']
            stats = self._compute_latency_stats(metrics)
            
            summary['adapters'][adapter_name] = {
                'status': 'completed',
                'operations': {
                    'total': adapter_data['total_operations'],
                    'success': adapter_data['success_count'],
                    'errors': adapter_data['error_count'],
                    'success_rate': adapter_data['success_rate']
                },
                'performance': {
                    'avg_latency_ms': stats['avg_latency'],
                    'p50_latency_ms': stats['p50_latency'],
                    'p95_latency_ms': stats['p95_latency'],
                    'p99_latency_ms': stats['p99_latency'],
                    'min_latency_ms': stats['min_latency'],
                    'max_latency_ms': stats['max_latency'],
                    'throughput_ops_sec': stats['throughput']
                },
                'backend_metrics': metrics.get('backend_metrics', {})
            }
        
        return summary
    
    def _compute_latency_stats(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """
        Compute latency statistics from metrics data.
        
        Args:
            metrics: Adapter metrics dictionary
        
        Returns:
            Statistics dictionary with avg, p50, p95, p99, throughput
        """
        # Collect all latencies from all operations
        all_latencies = []
        total_ops = 0
        total_time = 0.0
        
        operations = metrics.get('operations', {})
        
        for op_name, op_metrics in operations.items():
            if 'total_count' in op_metrics and op_metrics['total_count'] > 0:
                total_ops += op_metrics['total_count']
                
                # Use average latency if available
                if 'avg_latency_ms' in op_metrics:
                    avg = op_metrics['avg_latency_ms']
                    count = op_metrics['total_count']
                    all_latencies.extend([avg] * count)  # Approximate distribution
                    total_time += avg * count
        
        if not all_latencies:
            return {
                'avg_latency': 0.0,
                'p50_latency': 0.0,
                'p95_latency': 0.0,
                'p99_latency': 0.0,
                'min_latency': 0.0,
                'max_latency': 0.0,
                'throughput': 0.0
            }
        
        # Compute statistics
        all_latencies.sort()
        
        avg_latency = statistics.mean(all_latencies)
        min_latency = min(all_latencies)
        max_latency = max(all_latencies)
        
        # Percentiles
        p50_idx = len(all_latencies) // 2
        p95_idx = int(len(all_latencies) * 0.95)
        p99_idx = int(len(all_latencies) * 0.99)
        
        p50_latency = all_latencies[p50_idx]
        p95_latency = all_latencies[p95_idx]
        p99_latency = all_latencies[p99_idx]
        
        # Throughput (ops/sec)
        total_time_sec = total_time / 1000.0  # Convert ms to sec
        throughput = total_ops / total_time_sec if total_time_sec > 0 else 0.0
        
        return {
            'avg_latency': avg_latency,
            'p50_latency': p50_latency,
            'p95_latency': p95_latency,
            'p99_latency': p99_latency,
            'min_latency': min_latency,
            'max_latency': max_latency,
            'throughput': throughput
        }


def main():
    """Main entry point for analysis script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze benchmark results and generate tables'
    )
    parser.add_argument(
        '--results',
        type=str,
        help='Path to benchmark results JSON file (default: most recent)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output directory for tables (default: benchmarks/reports/tables)'
    )
    
    args = parser.parse_args()
    
    results_file = Path(args.results) if args.results else None
    output_dir = Path(args.output) if args.output else None
    
    analyzer = BenchmarkAnalyzer(results_file)
    analyzer.generate_all_tables(output_dir)
    
    print("\n" + "="*80)
    print("✓ Analysis complete!")
    print("="*80)


if __name__ == "__main__":
    main()
