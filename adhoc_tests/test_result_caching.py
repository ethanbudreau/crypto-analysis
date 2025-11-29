#!/usr/bin/env python3
"""
Test if Sirius caches query RESULTS (not just data).
We'll run the same query multiple times and see if timing changes.
"""
import subprocess
import tempfile
import os

sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")

def test_repeated_queries(dataset_size, buffer_min, buffer_max):
    """Run same query 5 times to see if results are cached."""

    # Simple 2-hop query
    query = """
    SELECT e2.txId2 AS connected_node, MAX(n3.class) AS node_class
    FROM nodes n1
    JOIN edges e1 ON n1.txId = e1.txId1
    JOIN nodes n2 ON e1.txId2 = n2.txId
    JOIN edges e2 ON n2.txId = e2.txId1
    JOIN nodes n3 ON e2.txId2 = n3.txId
    WHERE n1.class = '1' AND e2.txId2 != n1.txId
    GROUP BY e2.txId2
    ORDER BY e2.txId2
    LIMIT 100
    """.replace("'", "''")

    script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_{dataset_size}.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_{dataset_size}.csv');
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

.timer on
.print 'Query 1:'
call gpu_processing('{query}');

.print 'Query 2 (immediate repeat):'
call gpu_processing('{query}');

.print 'Query 3 (immediate repeat):'
call gpu_processing('{query}');

.print 'Query 4 (immediate repeat):'
call gpu_processing('{query}');

.print 'Query 5 (immediate repeat):'
call gpu_processing('{query}');
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(script)
        temp_file = f.name

    try:
        result = subprocess.run(
            [sirius_binary, "-init", temp_file],
            capture_output=True,
            text=True,
            timeout=120
        )

        print(f"\n{dataset_size} dataset:")
        print("="*70)

        if result.returncode == 0:
            # Extract timing lines
            for line in result.stdout.split('\n'):
                if 'Query' in line or 'Run Time' in line:
                    print(line)
        else:
            print(f"Error: {result.stderr[:500]}")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

print("="*70)
print("TESTING FOR QUERY RESULT CACHING")
print("="*70)
print("If times drop significantly after query 1, results are being cached.")
print("If times stay similar, only data is cached (correct behavior).")
print("="*70)

test_repeated_queries('5m', '4 GB', '8 GB')
test_repeated_queries('20m', '6 GB', '8 GB')

print("\n" + "="*70)
