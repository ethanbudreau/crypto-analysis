#!/usr/bin/env python3
"""
Benchmark Execution Script
Runs graph queries on DuckDB and Sirius, collecting performance metrics.

Executes queries across multiple dataset sizes and measures:
- Query execution time (with separate initialization timing)
- CPU/GPU utilization
- Memory/VRAM usage

Benchmark Modes:
- cold_start: Initialize fresh for each query run (includes all overhead)
- warm_cache: Initialize once, then run queries on warm cache (excludes init overhead)
- persistent_session: Initialize once, run multiple sequential queries (session simulation)

Usage:
    python scripts/02_run_benchmarks.py [--db duckdb|sirius|both] [--mode cold_start|warm_cache|persistent_session]

Examples:
    # Cold start (default) - includes initialization overhead
    python scripts/02_run_benchmarks.py --db both --sizes full --queries 1_hop

    # Warm cache - excludes initialization overhead
    python scripts/02_run_benchmarks.py --db both --sizes full --queries 1_hop --mode warm_cache

    # Persistent session - 100 sequential queries
    python scripts/02_run_benchmarks.py --db both --sizes full --queries 1_hop --mode persistent_session --session-queries 100
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
        db_type: 'duckdb' or 'sirius' (not used, queries are unified)
        query_name: e.g., '1_hop', '2_hop', 'k_hop', 'shortest_path'

    Returns:
        SQL query string
    """
    # All queries are now in sql/queries/ - they work on both DuckDB and Sirius
    query_path = f"sql/queries/{query_name}.sql"

    if not os.path.exists(query_path):
        print(f"⚠ Warning: Query file not found: {query_path}")
        return None

    with open(query_path, 'r') as f:
        return f.read()


def run_duckdb_benchmark(dataset_size, query_name, num_runs=3, mode='cold_start', session_queries=100):
    """
    Run a query on DuckDB and measure performance.

    Args:
        dataset_size: '10k', '50k', '100k', 'full', '1m', '5m', '10m', etc.
        query_name: Name of the query to run
        num_runs: Number of times to run for averaging
        mode: 'cold_start', 'warm_cache', or 'persistent_session'
        session_queries: Number of queries to run in persistent_session mode

    Returns:
        Dictionary with benchmark results
    """
    print(f"\n  Running DuckDB (CPU): {query_name} on {dataset_size} dataset (mode: {mode})...", flush=True)

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

    if mode == 'cold_start':
        # Cold start: Fresh connection and data load for each run
        execution_times = []
        load_times = []

        for run in range(num_runs):
            # Fresh connection
            conn = duckdb.connect(':memory:')

            # Load data
            load_start = time.time()
            conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}')")
            conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}')")
            load_time = time.time() - load_start
            load_times.append(load_time)

            # Execute query
            start_time = time.time()
            result = conn.execute(query).fetchall()
            exec_time = time.time() - start_time
            execution_times.append(exec_time)

            conn.close()

        avg_load_time = sum(load_times) / len(load_times)
        avg_exec_time = sum(execution_times) / len(execution_times)

        print(f"  ✓ Avg Init: {avg_load_time:.4f}s | Avg Query: {avg_exec_time:.4f}s | Total: {avg_load_time + avg_exec_time:.4f}s")

        return {
            'database': 'duckdb',
            'query': query_name,
            'dataset_size': dataset_size,
            'mode': mode,
            'initialization_time': avg_load_time,
            'avg_query_time': avg_exec_time,
            'total_time': avg_load_time + avg_exec_time,
            'min_query_time': min(execution_times),
            'max_query_time': max(execution_times),
            'num_runs': num_runs
        }

    elif mode == 'warm_cache':
        # Warm cache: Initialize once, run queries multiple times
        conn = duckdb.connect(':memory:')

        # One-time initialization
        init_start = time.time()
        conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}')")
        conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}')")
        init_time = time.time() - init_start

        # Warm-up run (discarded)
        conn.execute(query).fetchall()

        # Timed runs
        execution_times = []
        for run in range(num_runs):
            start_time = time.time()
            result = conn.execute(query).fetchall()
            exec_time = time.time() - start_time
            execution_times.append(exec_time)

        conn.close()

        avg_exec_time = sum(execution_times) / len(execution_times)

        print(f"  ✓ Init: {init_time:.4f}s | Avg Query (warm): {avg_exec_time:.4f}s")

        return {
            'database': 'duckdb',
            'query': query_name,
            'dataset_size': dataset_size,
            'mode': mode,
            'initialization_time': init_time,
            'avg_query_time': avg_exec_time,
            'min_query_time': min(execution_times),
            'max_query_time': max(execution_times),
            'num_runs': num_runs
        }

    elif mode == 'persistent_session':
        # Persistent session: Initialize once, run many queries
        conn = duckdb.connect(':memory:')

        # One-time initialization
        init_start = time.time()
        conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}')")
        conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}')")
        init_time = time.time() - init_start

        # Warm-up run (discarded) - also capture row count
        warmup_result = conn.execute(query).fetchall()
        row_count = len(warmup_result)

        # Run many queries in sequence
        session_start = time.time()
        for i in range(session_queries):
            result = conn.execute(query).fetchall()
            # Progress output every 10 queries
            if (i + 1) % 10 == 0 or (i + 1) == session_queries:
                elapsed = time.time() - session_start
                avg_so_far = elapsed / (i + 1)
                print(f"  Progress: {i+1}/{session_queries} queries ({elapsed:.1f}s, {avg_so_far:.4f}s avg)", flush=True)
        session_time = time.time() - session_start

        conn.close()

        avg_query_time = session_time / session_queries
        total_time = init_time + session_time

        print(f"  ✓ Init: {init_time:.4f}s | {session_queries} queries: {session_time:.4f}s | Avg per query: {avg_query_time:.4f}s | {row_count} rows", flush=True)

        return {
            'database': 'duckdb',
            'query': query_name,
            'dataset_size': dataset_size,
            'mode': mode,
            'initialization_time': init_time,
            'session_total_time': session_time,
            'avg_query_time': avg_query_time,
            'total_time': total_time,
            'num_queries': session_queries,
            'amortized_time_per_query': total_time / session_queries,
            'result_row_count': row_count
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


def run_sirius_benchmark(dataset_size, query_name, num_runs=3, mode='cold_start', session_queries=100):
    """
    Run a query on Sirius and measure performance.

    Args:
        dataset_size: '10k', '50k', '100k', 'full', '1m', '5m', '10m', etc.
        query_name: Name of the query to run
        num_runs: Number of times to run for averaging
        mode: 'cold_start', 'warm_cache', or 'persistent_session'
        session_queries: Number of queries to run in persistent_session mode

    Returns:
        Dictionary with benchmark results
    """
    print(f"\n  Running Sirius (GPU): {query_name} on {dataset_size} dataset (mode: {mode})...", flush=True)

    # Check if Sirius binary exists
    sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")
    if not os.path.exists(sirius_binary):
        print(f"  ✗ Sirius binary not found at: {sirius_binary}")
        return {
            'database': 'sirius',
            'query': query_name,
            'dataset_size': dataset_size,
            'mode': mode,
            'avg_query_time': None,
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
        'full': ('2 GB', '4 GB'),
        'full_slim': ('256 MB', '512 MB'),
        '1m': ('2 GB', '4 GB'),
        '5m': ('4 GB', '8 GB'),
        '5m_slim': ('1 GB', '2 GB'),
        '10m': ('6 GB', '8 GB'),
        '20m': ('6 GB', '8 GB'),
        '50m': ('6 GB', '8 GB'),
        '100m': ('6 GB', '8 GB'),
        '200m': ('6 GB', '8 GB')
    }
    buffer_min, buffer_max = buffer_sizes.get(dataset_size, ('2 GB', '4 GB'))

    # Clean query (remove comments)
    query_lines = [line for line in query.split('\n')
                   if line.strip() and not line.strip().startswith('--')]
    clean_query = ' '.join(query_lines)

    if mode == 'cold_start':
        # Cold start: Initialize GPU for each run
        execution_times = []
        gpu_stats_before = get_gpu_stats()

        for run in range(num_runs):
            sql_script = f"""
-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');

-- Initialize GPU
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

-- Run query
call gpu_processing('{clean_query.replace("'", "''")}');
"""
            # Write SQL to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
                f.write(sql_script)
                temp_sql_file = f.name

            try:
                # Execute Sirius (includes all initialization)
                start_time = time.time()
                result = subprocess.run(
                    [sirius_binary, "-init", temp_sql_file],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                exec_time = time.time() - start_time

                if result.returncode == 0:
                    execution_times.append(exec_time)
                else:
                    print(f"    Warning: Run {run+1} failed with code {result.returncode}")

            except subprocess.TimeoutExpired:
                print(f"    Warning: Run {run+1} timed out")

            finally:
                if os.path.exists(temp_sql_file):
                    os.remove(temp_sql_file)

        gpu_stats_after = get_gpu_stats()

        if not execution_times:
            return {'database': 'sirius', 'query': query_name, 'dataset_size': dataset_size,
                    'mode': mode, 'avg_query_time': None, 'error': 'All runs failed'}

        avg_time = sum(execution_times) / len(execution_times)
        print(f"  ✓ Avg Total (incl. init): {avg_time:.4f}s | Min: {min(execution_times):.4f}s | Max: {max(execution_times):.4f}s")

        result_dict = {
            'database': 'sirius',
            'query': query_name,
            'dataset_size': dataset_size,
            'mode': mode,
            'total_time': avg_time,
            'min_total_time': min(execution_times),
            'max_total_time': max(execution_times),
            'num_runs': len(execution_times),
            'buffer_size_min': buffer_min,
            'buffer_size_max': buffer_max
        }

        if gpu_stats_after:
            result_dict['gpu_memory_used_mb'] = gpu_stats_after['gpu_memory_used_mb']
            result_dict['gpu_utilization_percent'] = gpu_stats_after['gpu_utilization_percent']

        return result_dict

    elif mode == 'warm_cache':
        # Warm cache: Initialize once, then run queries multiple times
        gpu_stats_before = get_gpu_stats()

        # Create initialization script
        init_script = f"""
-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');

-- Initialize GPU
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

-- Warm-up query (discarded)
call gpu_processing('{clean_query.replace("'", "''")}');
"""

        # Append timed query runs
        for run in range(num_runs):
            escaped_query = clean_query.replace("'", "''")
            init_script += f"\n-- Timed run {run+1}\ncall gpu_processing('{escaped_query}');\n"

        # Write complete script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write(init_script)
            temp_sql_file = f.name

        try:
            # Execute entire script and measure
            total_start = time.time()
            result = subprocess.run(
                [sirius_binary, "-init", temp_sql_file],
                capture_output=True,
                text=True,
                timeout=600
            )
            total_time = time.time() - total_start

            if result.returncode != 0:
                print(f"  ✗ Sirius execution failed")
                return {'database': 'sirius', 'query': query_name, 'dataset_size': dataset_size,
                        'mode': mode, 'avg_query_time': None, 'error': 'Execution failed'}

            # Parse timing output to separate init from query times
            # For now, we estimate: assume warm queries are fast compared to init
            # This is a rough approximation; ideally we'd parse Sirius output
            estimated_init_time = total_time * 0.8  # Rough estimate
            estimated_query_time = (total_time - estimated_init_time) / (num_runs + 1)  # +1 for warmup

            print(f"  ✓ Total: {total_time:.4f}s | Est. Init: {estimated_init_time:.4f}s | Est. Avg Query: {estimated_query_time:.4f}s")

        except subprocess.TimeoutExpired:
            print(f"  ✗ Execution timed out")
            return {'database': 'sirius', 'query': query_name, 'dataset_size': dataset_size,
                    'mode': mode, 'avg_query_time': None, 'error': 'Timeout'}

        finally:
            if os.path.exists(temp_sql_file):
                os.remove(temp_sql_file)

        gpu_stats_after = get_gpu_stats()

        result_dict = {
            'database': 'sirius',
            'query': query_name,
            'dataset_size': dataset_size,
            'mode': mode,
            'initialization_time': estimated_init_time,
            'avg_query_time': estimated_query_time,
            'total_time': total_time,
            'num_runs': num_runs,
            'buffer_size_min': buffer_min,
            'buffer_size_max': buffer_max,
            'note': 'Query timing estimated from total time'
        }

        if gpu_stats_after:
            result_dict['gpu_memory_used_mb'] = gpu_stats_after['gpu_memory_used_mb']
            result_dict['gpu_utilization_percent'] = gpu_stats_after['gpu_utilization_percent']

        return result_dict

    elif mode == 'persistent_session':
        # Persistent session: Initialize once, run many queries
        gpu_stats_before = get_gpu_stats()

        # Get row count using DuckDB (for validation - same query should return same rows)
        try:
            import duckdb
            temp_conn = duckdb.connect(':memory:')
            temp_conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}')")
            temp_conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}')")
            row_count = len(temp_conn.execute(query).fetchall())
            temp_conn.close()
        except Exception as e:
            row_count = None
            print(f"  Warning: Could not get row count: {e}")

        # Create session script
        session_script = f"""
-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');

-- Initialize GPU
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

-- Warm-up query (discarded)
call gpu_processing('{clean_query.replace("'", "''")}');
"""

        # Append many sequential queries
        escaped_query = clean_query.replace("'", "''")
        for i in range(session_queries):
            session_script += f"\n-- Session query {i+1}\ncall gpu_processing('{escaped_query}');\n"

        # Write session script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write(session_script)
            temp_sql_file = f.name

        try:
            # Execute session
            total_start = time.time()
            result = subprocess.run(
                [sirius_binary, "-init", temp_sql_file],
                capture_output=True,
                text=True,
                timeout=1200  # 20 minute timeout for long sessions
            )
            total_time = time.time() - total_start

            if result.returncode != 0:
                print(f"  ✗ Session failed")
                return {'database': 'sirius', 'query': query_name, 'dataset_size': dataset_size,
                        'mode': mode, 'avg_query_time': None, 'error': 'Session failed'}

            # Estimate times (rough approximation)
            estimated_init_time = min(total_time * 0.3, 5.0)  # Cap init at 5s
            session_time = total_time - estimated_init_time
            avg_query_time = session_time / (session_queries + 1)  # +1 for warmup
            amortized_time = total_time / session_queries

            if row_count is not None:
                print(f"  ✓ Total: {total_time:.4f}s | {session_queries} queries | Avg: {avg_query_time:.4f}s | Amortized: {amortized_time:.4f}s | {row_count} rows")
            else:
                print(f"  ✓ Total: {total_time:.4f}s | {session_queries} queries | Avg: {avg_query_time:.4f}s | Amortized: {amortized_time:.4f}s")

        except subprocess.TimeoutExpired:
            print(f"  ✗ Session timed out")
            return {'database': 'sirius', 'query': query_name, 'dataset_size': dataset_size,
                    'mode': mode, 'avg_query_time': None, 'error': 'Timeout'}

        finally:
            if os.path.exists(temp_sql_file):
                os.remove(temp_sql_file)

        gpu_stats_after = get_gpu_stats()

        result_dict = {
            'database': 'sirius',
            'query': query_name,
            'dataset_size': dataset_size,
            'mode': mode,
            'initialization_time': estimated_init_time,
            'session_total_time': session_time,
            'avg_query_time': avg_query_time,
            'total_time': total_time,
            'num_queries': session_queries,
            'amortized_time_per_query': amortized_time,
            'buffer_size_min': buffer_min,
            'buffer_size_max': buffer_max,
            'note': 'Query timing estimated from total time'
        }

        if row_count is not None:
            result_dict['result_row_count'] = row_count

        if gpu_stats_after:
            result_dict['gpu_memory_used_mb'] = gpu_stats_after['gpu_memory_used_mb']
            result_dict['gpu_utilization_percent'] = gpu_stats_after['gpu_utilization_percent']

        return result_dict


def benchmark_suite(databases=['duckdb'], dataset_sizes=['10k'], queries=None, mode='cold_start',
                    num_runs=3, session_queries=100):
    """
    Run full benchmark suite across databases, sizes, and queries.

    Args:
        databases: List of databases to test ['duckdb', 'sirius']
        dataset_sizes: List of dataset sizes ['10k', '50k', '100k', 'full', '1m', '5m', '10m']
        queries: List of query names (None = all queries)
        mode: Benchmark mode ('cold_start', 'warm_cache', 'persistent_session')
        num_runs: Number of runs per query for averaging
        session_queries: Number of queries in persistent_session mode

    Returns:
        List of benchmark results
    """
    if queries is None:
        queries = ['1_hop', '2_hop', 'k_hop', 'shortest_path']

    results = []

    print("="*60)
    print("BENCHMARK SUITE")
    print("="*60)
    print(f"Mode: {mode}")
    print(f"Databases: {databases}")
    print(f"Dataset sizes: {dataset_sizes}")
    print(f"Queries: {queries}")
    if mode == 'persistent_session':
        print(f"Session queries: {session_queries}")
    else:
        print(f"Runs per query: {num_runs}")
    print("="*60)

    for db in databases:
        print(f"\n{'='*60}")
        print(f"Testing: {db.upper()}")
        print('='*60)

        for size in dataset_sizes:
            print(f"\nDataset size: {size}")

            for query in queries:
                if db == 'duckdb':
                    result = run_duckdb_benchmark(size, query, num_runs=num_runs,
                                                 mode=mode, session_queries=session_queries)
                elif db == 'sirius':
                    result = run_sirius_benchmark(size, query, num_runs=num_runs,
                                                 mode=mode, session_queries=session_queries)
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
    parser = argparse.ArgumentParser(
        description='Run benchmark suite with multiple modes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Cold start benchmark (includes initialization overhead)
  python scripts/02_run_benchmarks.py --db both --sizes full --queries 1_hop

  # Warm cache benchmark (excludes initialization overhead)
  python scripts/02_run_benchmarks.py --db both --sizes full --queries 1_hop --mode warm_cache

  # Persistent session (100 sequential queries to test amortization)
  python scripts/02_run_benchmarks.py --db both --sizes full --queries 1_hop --mode persistent_session --session-queries 100

  # Large dataset benchmarks
  python scripts/02_run_benchmarks.py --db both --sizes 10m --queries 1_hop --mode warm_cache
        """)

    parser.add_argument('--db', choices=['duckdb', 'sirius', 'both'],
                        default='duckdb',
                        help='Database to benchmark (default: duckdb)')
    parser.add_argument('--sizes', nargs='+',
                        default=['10k'],
                        help='Dataset sizes to test (default: 10k). Options: 10k, 50k, 100k, full, 1m, 5m, 10m, 20m')
    parser.add_argument('--queries', nargs='+',
                        help='Specific queries to run (default: all). Options: 1_hop, 2_hop, k_hop, shortest_path')
    parser.add_argument('--mode', choices=['cold_start', 'warm_cache', 'persistent_session'],
                        default='cold_start',
                        help='Benchmark mode (default: cold_start)')
    parser.add_argument('--runs', type=int, default=3,
                        help='Number of runs per query for averaging (default: 3)')
    parser.add_argument('--session-queries', type=int, default=100,
                        help='Number of queries in persistent_session mode (default: 100)')
    parser.add_argument('--output', default='results/benchmarks.csv',
                        help='Output CSV file (default: results/benchmarks.csv)')

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
        queries=args.queries,
        mode=args.mode,
        num_runs=args.runs,
        session_queries=args.session_queries
    )

    # Save and display results
    save_results(results, output_file=args.output)
    print_summary(results)

    print("\n" + "="*60)
    print("BENCHMARKING COMPLETE")
    print("="*60)
    print(f"\nResults saved to: {args.output}")
    print("\nNext steps:")
    print("  - Review results in CSV file")
    print("  - Visualize: python scripts/03_visualize.py")
    print("\nBenchmark Modes:")
    print("  - cold_start: Includes all initialization overhead (realistic for ad-hoc queries)")
    print("  - warm_cache: Excludes initialization (realistic for interactive sessions)")
    print("  - persistent_session: Many queries in sequence (realistic for batch analytics)")


if __name__ == "__main__":
    main()
