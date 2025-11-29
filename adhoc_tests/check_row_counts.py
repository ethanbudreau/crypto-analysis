#!/usr/bin/env python3
"""
Check row counts for 2-hop, 3-hop, and k-hop queries to understand timing differences.
"""
import subprocess
import tempfile
import os

sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")

queries = {
    '2-hop': """
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_20m.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_20m.csv');
call gpu_buffer_init('6 GB', '8 GB');
call gpu_processing('
SELECT COUNT(*) as row_count FROM (
  SELECT e2.txId2 AS connected_node, MAX(n3.class) AS node_class
  FROM nodes n1
  JOIN edges e1 ON n1.txId = e1.txId1
  JOIN nodes n2 ON e1.txId2 = n2.txId
  JOIN edges e2 ON n2.txId = e2.txId1
  JOIN nodes n3 ON e2.txId2 = n3.txId
  WHERE n1.class = ''1'' AND e2.txId2 != n1.txId
  GROUP BY e2.txId2
)');
""",
    '3-hop': """
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_20m.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_20m.csv');
call gpu_buffer_init('6 GB', '8 GB');
call gpu_processing('
SELECT COUNT(*) as row_count FROM (
  SELECT e3.txId2 AS node_id, MAX(n4.class) AS node_class
  FROM nodes n1
  JOIN edges e1 ON n1.txId = e1.txId1
  JOIN nodes n2 ON e1.txId2 = n2.txId
  JOIN edges e2 ON n2.txId = e2.txId1
  JOIN nodes n3 ON e2.txId2 = n3.txId
  JOIN edges e3 ON n3.txId = e3.txId1
  JOIN nodes n4 ON e3.txId2 = n4.txId
  WHERE n1.class = ''1'' AND e3.txId2 != n1.txId AND e3.txId2 != n2.txId
  GROUP BY e3.txId2
)');
""",
    'k-hop (1+2+3+4)': """
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_20m.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_20m.csv');
call gpu_buffer_init('6 GB', '8 GB');
-- Load the full k-hop query from file
.read sql/sirius/k_hop_gpu.sql
"""
}

def run_count_query(name, query_sql):
    print(f"\n{'='*60}")
    print(f"Counting rows: {name}")
    print('='*60)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(query_sql)
        temp_file = f.name

    try:
        result = subprocess.run(
            [sirius_binary, "-init", temp_file],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Extract row count from output
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'row_count' in line or line.strip().isdigit():
                    print(f"Output: {line}")

            # Try to find a number in the output
            import re
            numbers = re.findall(r'│\s*(\d+)\s*│', result.stdout)
            if numbers:
                count = numbers[-1]  # Take last number (likely the count)
                print(f"✅ Result: {count} rows")
                return int(count)
            else:
                print("⚠️  Could not extract count from output")
                print(f"Last 20 lines of output:")
                print('\n'.join(result.stdout.split('\n')[-20:]))
        else:
            print(f"❌ Query failed: {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr[:500]}")

        return None

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

print("="*60)
print("ROW COUNT ANALYSIS")
print("="*60)

counts = {}
for name, query in queries.items():
    if name != 'k-hop (1+2+3+4)':  # Skip k-hop for now, it's more complex
        count = run_count_query(name, query)
        if count:
            counts[name] = count

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
for name, count in counts.items():
    print(f"{name:20s}: {count:,} rows")

if '2-hop' in counts and '3-hop' in counts:
    ratio = counts['2-hop'] / counts['3-hop'] if counts['3-hop'] > 0 else 0
    print(f"\n2-hop returns {ratio:.2f}x more rows than 3-hop")
    print("\nThis likely explains why 3-hop is faster:")
    print("- Fewer result rows → less data to GROUP BY and ORDER BY")
    print("- Cycle detection filters out many paths in 3-hop")
