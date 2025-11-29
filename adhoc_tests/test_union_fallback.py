#!/usr/bin/env python3
"""
Test if UNION ALL causes full or partial GPU fallback.
Runs via subprocess to avoid CLI bugs.
"""
import subprocess
import tempfile
import os
import time

sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")

# Test queries
test_2hop = """
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_1m.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_1m.csv');
call gpu_buffer_init('2 GB', '4 GB');
call gpu_processing('
SELECT e2.txId2 AS node_id, MAX(n3.class) AS node_class, 2 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
WHERE n1.class = ''1'' AND e2.txId2 != n1.txId
GROUP BY e2.txId2
ORDER BY e2.txId2
');
"""

test_3hop = """
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_1m.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_1m.csv');
call gpu_buffer_init('2 GB', '4 GB');
call gpu_processing('
SELECT e3.txId2 AS node_id, MAX(n4.class) AS node_class, 3 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
JOIN edges e3 ON n3.txId = e3.txId1
JOIN nodes n4 ON e3.txId2 = n4.txId
WHERE n1.class = ''1'' AND e3.txId2 != n1.txId AND e3.txId2 != n2.txId
GROUP BY e3.txId2
ORDER BY e3.txId2
');
"""

test_union = """
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_1m.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_1m.csv');
call gpu_buffer_init('2 GB', '4 GB');
call gpu_processing('
SELECT e2.txId2 AS node_id, MAX(n3.class) AS node_class, 2 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
WHERE n1.class = ''1'' AND e2.txId2 != n1.txId
GROUP BY e2.txId2
UNION ALL
SELECT e3.txId2 AS node_id, MAX(n4.class) AS node_class, 3 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
JOIN edges e3 ON n3.txId = e3.txId1
JOIN nodes n4 ON e3.txId2 = n4.txId
WHERE n1.class = ''1'' AND e3.txId2 != n1.txId AND e3.txId2 != n2.txId
GROUP BY e3.txId2
ORDER BY node_id
');
"""

def run_test(name, query):
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print('='*60)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(query)
        temp_file = f.name

    try:
        start = time.time()
        result = subprocess.run(
            [sirius_binary, "-init", temp_file],
            capture_output=True,
            text=True,
            timeout=180
        )
        elapsed = time.time() - start

        # Check for GPU fallback
        if "Error in GPUExecuteQuery" in result.stdout or "Error in GPUExecuteQuery" in result.stderr:
            print(f"⚠️  GPU FALLBACK DETECTED")
        else:
            print(f"✅ GPU execution")

        # Check for errors
        if result.returncode != 0:
            print(f"❌ Failed with exit code {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr[:500]}")
        else:
            print(f"✅ Success")

        print(f"⏱️  Total time: {elapsed:.3f}s")

        # Extract query time from output
        for line in result.stdout.split('\n'):
            if 'Run Time (s): real' in line:
                parts = line.split()
                if len(parts) >= 4:
                    print(f"   Query time: {parts[3]}")

        return elapsed, "Error in GPUExecuteQuery" in result.stdout or "Error in GPUExecuteQuery" in result.stderr

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Run tests
print("="*60)
print("UNION ALL FALLBACK TEST")
print("="*60)

time_2hop, fallback_2hop = run_test("Test 1: 2-hop baseline", test_2hop)
time_3hop, fallback_3hop = run_test("Test 2: 3-hop baseline", test_3hop)
time_union, fallback_union = run_test("Test 3: UNION ALL (2-hop + 3-hop)", test_union)

# Analysis
print("\n" + "="*60)
print("ANALYSIS")
print("="*60)
print(f"2-hop time:  {time_2hop:.3f}s  {'(GPU fallback)' if fallback_2hop else '(GPU)'}")
print(f"3-hop time:  {time_3hop:.3f}s  {'(GPU fallback)' if fallback_3hop else '(GPU)'}")
print(f"UNION time:  {time_union:.3f}s  {'(GPU fallback)' if fallback_union else '(GPU)'}")
print()

if fallback_union:
    print("UNION ALL triggered GPU fallback")
    if time_union < time_2hop + time_3hop:
        print(f"  UNION time ({time_union:.3f}s) < sum ({time_2hop+time_3hop:.3f}s)")
        print("  → Suggests PARTIAL fallback (subqueries on GPU, UNION on CPU)")
    else:
        print(f"  UNION time ({time_union:.3f}s) ≈ sum ({time_2hop+time_3hop:.3f}s)")
        print("  → Suggests FULL fallback (entire query on CPU)")
else:
    print("UNION ALL ran on GPU successfully!")
