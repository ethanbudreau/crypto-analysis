#!/usr/bin/env python3
"""
Verify that DuckDB and Sirius return identical results for the same queries.
Also checks that Sirius queries run on GPU without CPU fallback.
"""

import subprocess
import sys
import tempfile
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Set
import json
import duckdb

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SIRIUS_BIN = str(PROJECT_ROOT / "sirius" / "build" / "release" / "duckdb")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
SQL_DIR = PROJECT_ROOT / "sql"

# Test configurations
TEST_DATASETS = ["10k", "100k"]  # Smaller datasets for quick verification
TEST_QUERIES = ["1_hop_gpu", "2_hop_gpu", "3_hop_gpu", "k_hop_gpu", "shortest_path_gpu"]

def run_duckdb_query(dataset_size: str, query_file: str) -> Tuple[List[List[str]], str]:
    """Run query on standard DuckDB and return results."""
    nodes_file = DATA_DIR / f"nodes_{dataset_size}.csv"
    edges_file = DATA_DIR / f"edges_{dataset_size}.csv"
    sql_file = SQL_DIR / "duckdb" / query_file

    if not sql_file.exists():
        raise FileNotFoundError(f"Query file not found: {sql_file}")

    with open(sql_file, 'r') as f:
        query_sql = f.read().strip()

    try:
        # Create in-memory DuckDB connection
        conn = duckdb.connect(":memory:")

        # Load data
        conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}')")
        conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}')")

        # Run query
        result = conn.execute(query_sql).fetchall()
        conn.close()

        # Convert to list of lists of strings for comparison
        rows = [[str(val) for val in row] for row in result]

        return rows, "OK"

    except Exception as e:
        return None, f"DuckDB error: {str(e)}"

def run_sirius_query(dataset_size: str, query_file: str) -> Tuple[List[List[str]], str, bool]:
    """
    Run query on Sirius and return results.
    Returns: (results, status_message, gpu_used)
    """
    nodes_file = DATA_DIR / f"nodes_{dataset_size}.csv"
    edges_file = DATA_DIR / f"edges_{dataset_size}.csv"
    sql_file = SQL_DIR / "sirius" / query_file

    if not sql_file.exists():
        raise FileNotFoundError(f"Query file not found: {sql_file}")

    with open(sql_file, 'r') as f:
        query_sql = f.read()

    # Remove comments but preserve line breaks
    lines = []
    for line in query_sql.split('\n'):
        # Remove comments but keep the SQL
        if '--' in line:
            line = line.split('--')[0]  # Keep part before comment
        line = line.rstrip()
        if line:  # Keep non-empty lines
            lines.append(line)
    actual_query = '\n'.join(lines)  # Use newlines to preserve SQL structure

    # Escape single quotes for gpu_processing call
    actual_query_escaped = actual_query.replace("'", "''")

    # Determine buffer sizes based on dataset
    buffer_configs = {
        "10k": ("256 MB", "512 MB"),
        "100k": ("1 GB", "2 GB"),
        "1m": ("2 GB", "4 GB"),
        "5m": ("4 GB", "8 GB"),
        "20m": ("6 GB", "8 GB"),
    }
    min_buf, max_buf = buffer_configs.get(dataset_size, ("1 GB", "2 GB"))

    # Build SQL script
    sql_script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');
call gpu_buffer_init('{min_buf}', '{max_buf}');
call gpu_processing('{actual_query_escaped}');
"""

    # Run Sirius - use stdin instead of -init because -csv doesn't work with -init
    try:
        result = subprocess.run(
            [SIRIUS_BIN, "-csv"],
            input=sql_script,
            capture_output=True,
            text=True,
            timeout=120
        )

        # Check for CPU fallback in stderr
        gpu_used = True
        if "fallback to DuckDB" in result.stderr or "Error in GPUExecuteQuery" in result.stderr:
            gpu_used = False

        if result.returncode != 0:
            return None, f"Sirius error: {result.stderr}", gpu_used

        # Parse CSV output
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:
            return [], "OK", gpu_used

        # Skip header and parse rows
        reader = csv.reader(lines)
        header = next(reader)
        rows = [row for row in reader]

        return rows, "OK", gpu_used

    except Exception as e:
        return None, f"Sirius exception: {str(e)}", False

def compare_results(duckdb_results: List[List[str]], sirius_results: List[List[str]]) -> Tuple[bool, str]:
    """Compare two result sets and return whether they match."""
    if duckdb_results is None or sirius_results is None:
        return False, "One or both queries failed"

    # Convert to sets for comparison (order might differ)
    duckdb_set = set(tuple(row) for row in duckdb_results)
    sirius_set = set(tuple(row) for row in sirius_results)

    if duckdb_set == sirius_set:
        return True, f"Match: {len(duckdb_results)} rows"

    # Find differences
    only_in_duckdb = duckdb_set - sirius_set
    only_in_sirius = sirius_set - duckdb_set

    msg = f"MISMATCH: DuckDB={len(duckdb_results)} rows, Sirius={len(sirius_results)} rows"
    if only_in_duckdb:
        msg += f", {len(only_in_duckdb)} only in DuckDB"
    if only_in_sirius:
        msg += f", {len(only_in_sirius)} only in Sirius"

    return False, msg

def verify_all():
    """Run all verification tests."""
    print("=" * 80)
    print("QUERY RESULT VERIFICATION")
    print("=" * 80)
    print()

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    gpu_fallback_tests = 0

    results = []

    for dataset in TEST_DATASETS:
        print(f"Dataset: {dataset}")
        print("-" * 80)

        for query in TEST_QUERIES:
            query_file = f"{query}.sql"
            total_tests += 1

            print(f"  [{total_tests}] Testing {query}...", end=" ", flush=True)

            # Run on DuckDB
            duckdb_results, duckdb_msg = run_duckdb_query(dataset, query_file)
            if duckdb_results is None:
                print(f"❌ FAILED - DuckDB: {duckdb_msg}")
                failed_tests += 1
                results.append({
                    "dataset": dataset,
                    "query": query,
                    "status": "FAILED",
                    "reason": duckdb_msg,
                    "gpu_used": "N/A"
                })
                continue

            # Run on Sirius
            sirius_results, sirius_msg, gpu_used = run_sirius_query(dataset, query_file)
            if sirius_results is None:
                print(f"❌ FAILED - Sirius: {sirius_msg}")
                failed_tests += 1
                results.append({
                    "dataset": dataset,
                    "query": query,
                    "status": "FAILED",
                    "reason": sirius_msg,
                    "gpu_used": gpu_used
                })
                continue

            # Compare results
            match, comparison_msg = compare_results(duckdb_results, sirius_results)

            if not gpu_used:
                gpu_fallback_tests += 1
                print(f"⚠️  CPU FALLBACK - {comparison_msg}")
                results.append({
                    "dataset": dataset,
                    "query": query,
                    "status": "CPU_FALLBACK",
                    "reason": comparison_msg,
                    "gpu_used": False
                })
            elif match:
                print(f"✅ PASS - {comparison_msg}")
                passed_tests += 1
                results.append({
                    "dataset": dataset,
                    "query": query,
                    "status": "PASS",
                    "reason": comparison_msg,
                    "gpu_used": True
                })
            else:
                print(f"❌ FAILED - {comparison_msg}")
                failed_tests += 1
                results.append({
                    "dataset": dataset,
                    "query": query,
                    "status": "MISMATCH",
                    "reason": comparison_msg,
                    "gpu_used": gpu_used
                })

        print()

    # Summary
    print("=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"⚠️  CPU Fallback: {gpu_fallback_tests}")
    print()

    if failed_tests > 0:
        print("⚠️  VERIFICATION FAILED - Some queries returned different results!")
        print()
        print("Failed tests:")
        for r in results:
            if r["status"] in ["FAILED", "MISMATCH"]:
                print(f"  - {r['dataset']}/{r['query']}: {r['reason']}")
        return 1

    if gpu_fallback_tests > 0:
        print("⚠️  WARNING - Some queries fell back to CPU!")
        print()
        print("CPU fallback tests:")
        for r in results:
            if r["status"] == "CPU_FALLBACK":
                print(f"  - {r['dataset']}/{r['query']}")
        print()
        print("These queries may not benefit from GPU acceleration.")
        return 2

    print("✅ ALL TESTS PASSED - DuckDB and Sirius return identical results!")
    print("✅ All Sirius queries ran on GPU (no CPU fallback)")
    return 0

if __name__ == "__main__":
    sys.exit(verify_all())
