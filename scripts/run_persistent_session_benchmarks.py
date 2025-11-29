#!/usr/bin/env python3
"""
Persistent Session Benchmark Runner
====================================

All-in-one script to run comprehensive persistent session benchmarks
across multiple dataset sizes for both DuckDB and Sirius.

This script tests:
- Dataset sizes: 100k, 1m, 5m, 20m edges
- All GPU-compatible queries: 1_hop_gpu, 2_hop_gpu, 3_hop_gpu, k_hop_gpu, shortest_path_gpu
- Persistent session mode: 100 sequential queries per test
- Both DuckDB (CPU baseline) and Sirius (GPU) databases

Outputs consistent CSV format for easy analysis.

Usage:
    python scripts/run_persistent_session_benchmarks.py [--db duckdb|sirius|both] [--quick]

Options:
    --db: Which database to test (default: both)
    --quick: Run quick test with 10 queries instead of 100
    --session-queries: Number of queries per session (default: 100)
    --output-dir: Directory for results (default: results/persistent_session)
"""

import argparse
import os
import sys
import time
from pathlib import Path
import csv
from datetime import datetime

# Import benchmark functions using importlib to handle numeric filename
import importlib.util
spec = importlib.util.spec_from_file_location("run_benchmarks",
                                                str(Path(__file__).parent / "02_run_benchmarks.py"))
run_benchmarks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_benchmarks)
run_duckdb_benchmark = run_benchmarks.run_duckdb_benchmark
run_sirius_benchmark = run_benchmarks.run_sirius_benchmark

# Test configuration
DATASET_SIZES = ['100k', '1m', '5m', '20m']
# All GPU queries including k_hop and shortest_path (which use UNION ALL with partial fallback)
GPU_QUERIES = ['1_hop', '2_hop', '3_hop', 'k_hop', 'shortest_path']
DEFAULT_SESSION_QUERIES = 100

def ensure_dataset_exists(dataset_size):
    """Check if dataset files exist."""
    nodes_file = f'data/processed/nodes_{dataset_size}.csv'
    edges_file = f'data/processed/edges_{dataset_size}.csv'

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print(f"  ⚠️  Dataset {dataset_size} not found")
        print(f"     Missing: {nodes_file} or {edges_file}")
        return False
    return True

def run_comprehensive_benchmark(databases=['both'], session_queries=100, output_dir='results/persistent_session'):
    """
    Run comprehensive persistent session benchmarks.

    Args:
        databases: List of databases to test ['duckdb', 'sirius', 'both']
        session_queries: Number of queries per persistent session
        output_dir: Directory to save results

    Returns:
        List of all benchmark results
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Expand 'both' to individual databases
    if 'both' in databases:
        databases = ['duckdb', 'sirius']

    print("=" * 80)
    print("PERSISTENT SESSION BENCHMARK SUITE")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Databases: {', '.join(databases)}")
    print(f"Dataset sizes: {', '.join(DATASET_SIZES)}")
    print(f"Queries: {', '.join(GPU_QUERIES)}")
    print(f"Session queries: {session_queries}")
    print(f"Output directory: {output_dir}")
    print("=" * 80)

    all_results = []
    total_tests = len(databases) * len(DATASET_SIZES) * len(GPU_QUERIES)
    current_test = 0

    for db in databases:
        print(f"\n{'='*80}")
        print(f"TESTING DATABASE: {db.upper()}")
        print(f"{'='*80}")

        for size in DATASET_SIZES:
            print(f"\n{'-'*80}")
            print(f"Dataset Size: {size}")
            print(f"{'-'*80}")

            # Check if dataset exists
            if not ensure_dataset_exists(size):
                print(f"  ⏭️  Skipping {size} dataset (not found)")
                current_test += len(GPU_QUERIES)
                continue

            for query in GPU_QUERIES:
                current_test += 1
                print(f"\n[{current_test}/{total_tests}] {db.upper()} | {size} | {query}", flush=True)
                print("-" * 80, flush=True)

                start_time = time.time()

                try:
                    if db == 'duckdb':
                        result = run_duckdb_benchmark(
                            dataset_size=size,
                            query_name=query,
                            num_runs=1,  # Not used in persistent session mode
                            mode='persistent_session',
                            session_queries=session_queries
                        )
                    elif db == 'sirius':
                        result = run_sirius_benchmark(
                            dataset_size=size,
                            query_name=query,
                            num_runs=1,  # Not used in persistent session mode
                            mode='persistent_session',
                            session_queries=session_queries
                        )
                    else:
                        print(f"  ❌ Unknown database: {db}")
                        continue

                    if result:
                        result['test_timestamp'] = datetime.now().isoformat()
                        result['elapsed_seconds'] = time.time() - start_time
                        all_results.append(result)

                        # Print summary
                        if 'avg_query_time' in result and result['avg_query_time']:
                            print(f"  ✅ Success: {result['avg_query_time']:.4f}s avg per query", flush=True)
                        else:
                            print(f"  ⚠️  Completed with warnings", flush=True)
                    else:
                        print(f"  ❌ Failed: No result returned", flush=True)

                except Exception as e:
                    print(f"  ❌ Error: {str(e)}", flush=True)
                    import traceback
                    traceback.print_exc()
                    all_results.append({
                        'database': db,
                        'dataset_size': size,
                        'query': query,
                        'mode': 'persistent_session',
                        'error': str(e),
                        'test_timestamp': datetime.now().isoformat()
                    })

    return all_results

def save_results(results, output_dir='results/persistent_session'):
    """Save results to CSV files."""
    if not results:
        print("\n⚠️  No results to save")
        return

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save combined results
    combined_file = f'{output_dir}/all_results_{timestamp}.csv'

    # Get all unique field names from all results
    fieldnames = set()
    for result in results:
        fieldnames.update(result.keys())
    fieldnames = sorted(list(fieldnames))

    with open(combined_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Saved combined results: {combined_file}")

    # Also save per-database results
    for db in set(r.get('database') for r in results if r.get('database')):
        db_results = [r for r in results if r.get('database') == db]
        db_file = f'{output_dir}/{db}_results_{timestamp}.csv'

        with open(db_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(db_results)

        print(f"✅ Saved {db} results: {db_file}")

    return combined_file

def print_summary(results):
    """Print summary of benchmark results."""
    if not results:
        print("\n⚠️  No results to summarize")
        return

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    # Count successes and failures
    successful = [r for r in results if r.get('avg_query_time') is not None]
    failed = [r for r in results if r.get('avg_query_time') is None or r.get('error')]

    print(f"\nTotal tests: {len(results)}")
    print(f"Successful: {len(successful)} ✅")
    print(f"Failed: {len(failed)} ❌")

    if successful:
        print("\n" + "-" * 80)
        print("TOP 5 FASTEST (avg query time):")
        print("-" * 80)
        sorted_results = sorted(successful, key=lambda x: x.get('avg_query_time', float('inf')))
        for i, r in enumerate(sorted_results[:5], 1):
            print(f"{i}. {r['database']:8s} | {r['dataset_size']:5s} | {r['query']:20s} | {r['avg_query_time']:.4f}s")

        print("\n" + "-" * 80)
        print("TOP 5 SLOWEST (avg query time):")
        print("-" * 80)
        for i, r in enumerate(sorted_results[-5:][::-1], 1):
            print(f"{i}. {r['database']:8s} | {r['dataset_size']:5s} | {r['query']:20s} | {r['avg_query_time']:.4f}s")

    # Per-database summary
    for db in set(r.get('database') for r in results if r.get('database')):
        db_results = [r for r in successful if r.get('database') == db]
        if db_results:
            avg_time = sum(r.get('avg_query_time', 0) for r in db_results) / len(db_results)
            print(f"\n{db.upper()}: {len(db_results)} tests, avg {avg_time:.4f}s per query")

    if failed:
        print("\n" + "-" * 80)
        print("FAILED TESTS:")
        print("-" * 80)
        for r in failed:
            error = r.get('error', 'Unknown error')
            print(f"❌ {r.get('database', '?'):8s} | {r.get('dataset_size', '?'):5s} | {r.get('query', '?'):20s} | {error}")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Run comprehensive persistent session benchmarks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full benchmark suite (both databases, all sizes, 100 queries each)
  python scripts/run_persistent_session_benchmarks.py

  # Quick test with 10 queries per session
  python scripts/run_persistent_session_benchmarks.py --quick

  # Only test Sirius GPU
  python scripts/run_persistent_session_benchmarks.py --db sirius

  # Custom number of session queries
  python scripts/run_persistent_session_benchmarks.py --session-queries 50
        """
    )

    parser.add_argument('--db', choices=['duckdb', 'sirius', 'both'],
                        default='both',
                        help='Database to benchmark (default: both)')
    parser.add_argument('--quick', action='store_true',
                        help='Quick test with 10 queries per session')
    parser.add_argument('--session-queries', type=int, default=DEFAULT_SESSION_QUERIES,
                        help=f'Number of queries per session (default: {DEFAULT_SESSION_QUERIES})')
    parser.add_argument('--output-dir', default='results/persistent_session',
                        help='Output directory for results (default: results/persistent_session)')

    args = parser.parse_args()

    # Override session queries if --quick is specified
    session_queries = 10 if args.quick else args.session_queries

    # Expand database selection
    databases = [args.db] if args.db != 'both' else ['duckdb', 'sirius']

    print("\n🚀 Starting persistent session benchmarks...")
    print(f"   Mode: {'QUICK TEST' if args.quick else 'FULL BENCHMARK'}")

    # Run benchmarks
    results = run_comprehensive_benchmark(
        databases=databases,
        session_queries=session_queries,
        output_dir=args.output_dir
    )

    # Save results
    output_file = save_results(results, output_dir=args.output_dir)

    # Print summary
    print_summary(results)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    if output_file:
        print(f"\n📊 Results saved to: {output_file}")
    print("\nNext steps:")
    print("  - Review CSV files in results/persistent_session/")
    print("  - Analyze performance trends across dataset sizes")
    print("  - Compare DuckDB vs Sirius performance")
    print("  - Check for any failed tests and investigate")

if __name__ == "__main__":
    main()
