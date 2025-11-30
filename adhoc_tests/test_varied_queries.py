#!/usr/bin/env python3
"""
Test with VARIED queries to prevent caching
Each query has a slightly different WHERE clause to ensure unique execution
"""

import subprocess
import tempfile
import time
import os

def test_varied_queries_sirius(num_queries=100):
    """Run varied 2-hop queries on Sirius to prevent caching"""

    sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")
    nodes_file = os.path.abspath("data/processed/nodes_5m.csv")
    edges_file = os.path.abspath("data/processed/edges_5m.csv")

    # Build SQL script with varied queries
    sql_script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');
call gpu_buffer_init('4 GB', '8 GB');

-- Warm-up query
call gpu_processing('SELECT e2.txId2 AS connected_node, MAX(n3.class) AS node_class FROM nodes n1 JOIN edges e1 ON n1.txId = e1.txId1 JOIN nodes n2 ON e1.txId2 = n2.txId JOIN edges e2 ON n2.txId = e2.txId1 JOIN nodes n3 ON e2.txId2 = n3.txId WHERE n1.class = ''1'' AND e2.txId2 != n1.txId AND n1.txId > 0 GROUP BY e2.txId2 ORDER BY e2.txId2');
"""

    # Add varied queries - each with different txId threshold
    for i in range(num_queries):
        # Vary the txId threshold to make each query unique
        # Use small increments so results are similar but not identical
        threshold = i % 100  # Cycle through 0-99
        query = f"call gpu_processing('SELECT e2.txId2 AS connected_node, MAX(n3.class) AS node_class FROM nodes n1 JOIN edges e1 ON n1.txId = e1.txId1 JOIN nodes n2 ON e1.txId2 = n2.txId JOIN edges e2 ON n2.txId = e2.txId1 JOIN nodes n3 ON e2.txId2 = n3.txId WHERE n1.class = ''1'' AND e2.txId2 != n1.txId AND n1.txId > {threshold} GROUP BY e2.txId2 ORDER BY e2.txId2');"
        sql_script += f"\n{query}"

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(sql_script)
        temp_sql_file = f.name

    try:
        print("=" * 80)
        print("VARIED QUERIES TEST - SIRIUS GPU")
        print("=" * 80)
        print(f"Dataset: 5m edges")
        print(f"Queries: {num_queries} (each with unique WHERE clause)")
        print(f"Query type: 2-hop graph traversal")
        print("=" * 80)
        print()

        # Execute with timing
        start_time = time.time()
        result = subprocess.run(
            [sirius_binary, "-init", temp_sql_file],
            capture_output=True,
            text=True,
            timeout=600
        )
        total_time = time.time() - start_time

        if result.returncode != 0:
            print("ERROR:", result.stderr)
            return None

        # Parse output for row counts
        lines = result.stdout.split('\n')
        row_counts = [line for line in lines if 'rows' in line.lower()]

        print(f"\nTotal execution time: {total_time:.2f}s")
        print(f"Average per query: {(total_time / (num_queries + 1)):.4f}s")  # +1 for warmup
        print(f"Estimated session time (excluding init ~3s): {(total_time - 3):.2f}s")
        print(f"Estimated avg per query (excluding init): {((total_time - 3) / num_queries):.4f}s")
        print()
        print(f"Sample output lines: {len(row_counts)} result sets found")
        if row_counts:
            print(f"First result: {row_counts[0]}")
            print(f"Last result: {row_counts[-1]}")

        return {
            'total_time': total_time,
            'num_queries': num_queries,
            'avg_per_query': (total_time - 3) / num_queries
        }

    finally:
        if os.path.exists(temp_sql_file):
            os.remove(temp_sql_file)

if __name__ == "__main__":
    test_varied_queries_sirius(num_queries=100)
