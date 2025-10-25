#!/usr/bin/env python3
"""
Benchmark Execution Script
Runs graph queries on DuckDB and Sirius, collecting performance metrics.

Executes queries across multiple dataset sizes and measures:
- Query execution time
- CPU/GPU utilization
- Memory/VRAM usage

Usage:
    python scripts/02_run_benchmarks.py [--db duckdb|sirius|both]
"""

import argparse
import time
import os
import json
import csv
import subprocess
import tempfile
from pathlib import Path
import duckdb

# Optional: GPU monitoring (requires py3nvml)
try:
    import py3nvml.py3nvml as nvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False


def load_sql_query(db_type, query_name):
    """
    Load SQL query from file.

    Args:
        db_type: 'duckdb' or 'sirius'
        query_name: e.g., '1_hop', '2_hop', 'k_hop', 'shortest_path'

    Returns:
        SQL query string
    """
    query_path = f"sql/{db_type}/{query_name}.sql"

    if not os.path.exists(query_path):
        print(f"⚠ Warning: Query file not found: {query_path}")
        return None

    with open(query_path, 'r') as f:
        return f.read()


def run_duckdb_benchmark(dataset_size, query_name, num_runs=3):
    """
    Run a query on DuckDB and measure performance.

    Args:
        dataset_size: '10k', '50k', '100k', 'full'
        query_name: Name of the query to run
        num_runs: Number of times to run for averaging

    Returns:
        Dictionary with benchmark results
    """
    print(f"\n  Running DuckDB: {query_name} on {dataset_size} dataset...")

    # Load query
    query = load_sql_query('duckdb', query_name)
    if query is None:
        return None

    # Load data
    nodes_file = f"data/processed/nodes_{dataset_size}.csv"
    edges_file = f"data/processed/edges_{dataset_size}.csv"

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print(f"  ✗ Dataset files not found for {dataset_size}")
        return None

    # Connect to DuckDB
    conn = duckdb.connect(':memory:')

    # Load data into DuckDB
    load_start = time.time()
    conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}')")
    conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}')")
    load_time = time.time() - load_start

    # Run query multiple times
    execution_times = []
    for run in range(num_runs):
        start_time = time.time()
        result = conn.execute(query).fetchall()
        exec_time = time.time() - start_time
        execution_times.append(exec_time)

    conn.close()

    # Calculate statistics
    avg_time = sum(execution_times) / len(execution_times)
    min_time = min(execution_times)
    max_time = max(execution_times)

    print(f"  ✓ Avg: {avg_time:.4f}s | Min: {min_time:.4f}s | Max: {max_time:.4f}s")

    return {
        'database': 'duckdb',
        'query': query_name,
        'dataset_size': dataset_size,
        'load_time': load_time,
        'avg_execution_time': avg_time,
        'min_execution_time': min_time,
        'max_execution_time': max_time,
        'num_runs': num_runs
    }


def get_gpu_stats():
    """
    Get current GPU memory and utilization stats.

    Returns:
        Dictionary with GPU stats or None if unavailable
    """
    if not NVML_AVAILABLE:
        return None

    try:
        nvml.nvmlInit()
        handle = nvml.nvmlDeviceGetHandleByIndex(0)  # GPU 0

        mem_info = nvml.nvmlDeviceGetMemoryInfo(handle)
        utilization = nvml.nvmlDeviceGetUtilizationRates(handle)

        stats = {
            'gpu_memory_used_mb': mem_info.used / (1024 ** 2),
            'gpu_memory_total_mb': mem_info.total / (1024 ** 2),
            'gpu_utilization_percent': utilization.gpu
        }

        nvml.nvmlShutdown()
        return stats
    except Exception as e:
        print(f"    Warning: Could not get GPU stats: {e}")
        return None


def run_sirius_benchmark(dataset_size, query_name, num_runs=3):
    """
    Run a query on Sirius and measure performance.

    Args:
        dataset_size: '10k', '50k', '100k', 'full'
        query_name: Name of the query to run
        num_runs: Number of times to run for averaging

    Returns:
        Dictionary with benchmark results
    """
    print(f"\n  Running Sirius: {query_name} on {dataset_size} dataset...")

    # Check if Sirius binary exists
    sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")
    if not os.path.exists(sirius_binary):
        print(f"  ✗ Sirius binary not found at: {sirius_binary}")
        return {
            'database': 'sirius',
            'query': query_name,
            'dataset_size': dataset_size,
            'avg_execution_time': None,
            'error': 'Sirius binary not found'
        }

    # Load query
    query = load_sql_query('sirius', query_name)
    if query is None:
        return None

    # Load data file paths
    nodes_file = os.path.abspath(f"data/processed/nodes_{dataset_size}.csv")
    edges_file = os.path.abspath(f"data/processed/edges_{dataset_size}.csv")

    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print(f"  ✗ Dataset files not found for {dataset_size}")
        return None

    # Determine GPU buffer size based on dataset size
    buffer_sizes = {
        '10k': ('256 MB', '512 MB'),
        '50k': ('512 MB', '1 GB'),
        '100k': ('1 GB', '2 GB'),
        'full': ('2 GB', '4 GB')
    }
    buffer_min, buffer_max = buffer_sizes.get(dataset_size, ('512 MB', '1 GB'))

    # Clean query (remove comments)
    query_lines = [line for line in query.split('\n')
                   if line.strip() and not line.strip().startswith('--')]
    clean_query = ' '.join(query_lines)

    # Create SQL script for Sirius
    sql_script = f"""
-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');

-- Initialize GPU
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

-- Run query (timing handled externally)
call gpu_processing('{clean_query.replace("'", "''")}');
"""

    # Run benchmark multiple times
    execution_times = []
    gpu_stats_before = get_gpu_stats()

    for run in range(num_runs):
        # Write SQL to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write(sql_script)
            temp_sql_file = f.name

        try:
            # Execute Sirius
            start_time = time.time()
            result = subprocess.run(
                [sirius_binary, "-init", temp_sql_file],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            exec_time = time.time() - start_time

            if result.returncode == 0:
                execution_times.append(exec_time)
            else:
                print(f"    Warning: Run {run+1} failed with code {result.returncode}")
                if result.stderr:
                    print(f"    Error: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            print(f"    Warning: Run {run+1} timed out")

        finally:
            # Clean up temp file
            if os.path.exists(temp_sql_file):
                os.remove(temp_sql_file)

    gpu_stats_after = get_gpu_stats()

    if not execution_times:
        print(f"  ✗ All runs failed")
        return {
            'database': 'sirius',
            'query': query_name,
            'dataset_size': dataset_size,
            'avg_execution_time': None,
            'error': 'All benchmark runs failed'
        }

    # Calculate statistics
    avg_time = sum(execution_times) / len(execution_times)
    min_time = min(execution_times)
    max_time = max(execution_times)

    print(f"  ✓ Avg: {avg_time:.4f}s | Min: {min_time:.4f}s | Max: {max_time:.4f}s")

    result_dict = {
        'database': 'sirius',
        'query': query_name,
        'dataset_size': dataset_size,
        'avg_execution_time': avg_time,
        'min_execution_time': min_time,
        'max_execution_time': max_time,
        'num_runs': len(execution_times),
        'successful_runs': len(execution_times),
        'buffer_size_min': buffer_min,
        'buffer_size_max': buffer_max
    }

    # Add GPU stats if available
    if gpu_stats_after:
        result_dict['gpu_memory_used_mb'] = gpu_stats_after['gpu_memory_used_mb']
        result_dict['gpu_utilization_percent'] = gpu_stats_after['gpu_utilization_percent']

    return result_dict


def benchmark_suite(databases=['duckdb'], dataset_sizes=['10k'], queries=None):
    """
    Run full benchmark suite across databases, sizes, and queries.

    Args:
        databases: List of databases to test ['duckdb', 'sirius']
        dataset_sizes: List of dataset sizes ['10k', '50k', '100k', 'full']
        queries: List of query names (None = all queries)

    Returns:
        List of benchmark results
    """
    if queries is None:
        queries = ['1_hop', '2_hop', 'k_hop', 'shortest_path']

    results = []

    print("="*60)
    print("BENCHMARK SUITE")
    print("="*60)
    print(f"Databases: {databases}")
    print(f"Dataset sizes: {dataset_sizes}")
    print(f"Queries: {queries}")
    print("="*60)

    for db in databases:
        print(f"\n{'='*60}")
        print(f"Testing: {db.upper()}")
        print('='*60)

        for size in dataset_sizes:
            print(f"\nDataset size: {size}")

            for query in queries:
                if db == 'duckdb':
                    result = run_duckdb_benchmark(size, query)
                elif db == 'sirius':
                    result = run_sirius_benchmark(size, query)
                else:
                    print(f"  ✗ Unknown database: {db}")
                    continue

                if result:
                    results.append(result)

    return results


def save_results(results, output_file='results/benchmarks.csv'):
    """
    Save benchmark results to CSV file.

    Args:
        results: List of benchmark result dictionaries
        output_file: Path to output CSV file
    """
    if not results:
        print("\n⚠ No results to save")
        return

    # Ensure results directory exists
    Path("results").mkdir(exist_ok=True)

    # Get all possible keys from results
    fieldnames = set()
    for result in results:
        fieldnames.update(result.keys())
    fieldnames = sorted(list(fieldnames))

    # Write to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✓ Results saved to: {output_file}")


def print_summary(results):
    """Print summary of benchmark results."""
    if not results:
        return

    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)

    for result in results:
        db = result.get('database', 'unknown')
        query = result.get('query', 'unknown')
        size = result.get('dataset_size', 'unknown')
        avg_time = result.get('avg_execution_time', None)

        if avg_time:
            print(f"{db:10} | {query:15} | {size:10} | {avg_time:.4f}s")
        else:
            print(f"{db:10} | {query:15} | {size:10} | Not available")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Run benchmark suite')
    parser.add_argument('--db', choices=['duckdb', 'sirius', 'both'],
                        default='duckdb',
                        help='Database to benchmark (default: duckdb)')
    parser.add_argument('--sizes', nargs='+',
                        default=['10k'],
                        help='Dataset sizes to test (default: 10k)')
    parser.add_argument('--queries', nargs='+',
                        help='Specific queries to run (default: all)')

    args = parser.parse_args()

    # Determine which databases to test
    if args.db == 'both':
        databases = ['duckdb', 'sirius']
    else:
        databases = [args.db]

    # Run benchmarks
    results = benchmark_suite(
        databases=databases,
        dataset_sizes=args.sizes,
        queries=args.queries
    )

    # Save and display results
    save_results(results)
    print_summary(results)

    print("\n" + "="*60)
    print("BENCHMARKING COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("  - Review results: results/benchmarks.csv")
    print("  - Visualize: python scripts/03_visualize.py")


if __name__ == "__main__":
    main()
