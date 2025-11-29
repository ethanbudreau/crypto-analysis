#!/usr/bin/env python3
"""
Check actual result row counts for k_hop and shortest_path queries.
If result sizes are similar, that could explain why GPU times don't scale.
"""
import duckdb
import time

datasets = ['5m', '20m']

print("="*70)
print("RESULT SET SIZE ANALYSIS")
print("="*70)

for dataset in datasets:
    print(f"\n{'='*70}")
    print(f"Dataset: {dataset}")
    print('='*70)

    conn = duckdb.connect(':memory:')

    try:
        # Load data
        print(f"Loading {dataset} data...")
        conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_{dataset}.csv')")
        conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_{dataset}.csv')")

        # Test k_hop query
        print("\nRunning k_hop query...")
        start = time.time()
        with open('sql/duckdb/k_hop_gpu.sql', 'r') as f:
            # Filter out comment lines and reconstruct query
            lines = [line for line in f.readlines() if not line.strip().startswith('--')]
            query = ''.join(lines).strip().rstrip(';')
        result = conn.execute(f"SELECT COUNT(*) FROM ({query})")
        count = result.fetchone()[0]
        elapsed = time.time() - start
        print(f"✓ k_hop result: {count:,} rows ({elapsed:.2f}s)")

        # Test shortest_path query
        print("\nRunning shortest_path query...")
        start = time.time()
        with open('sql/duckdb/shortest_path_gpu.sql', 'r') as f:
            # Filter out comment lines and reconstruct query
            lines = [line for line in f.readlines() if not line.strip().startswith('--')]
            query = ''.join(lines).strip().rstrip(';')
        result = conn.execute(f"SELECT COUNT(*) FROM ({query})")
        count = result.fetchone()[0]
        elapsed = time.time() - start
        print(f"✓ shortest_path result: {count:,} rows ({elapsed:.2f}s)")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

print("\n" + "="*70)
print("If result counts are similar between 5m and 20m, that would")
print("explain why GPU query times are identical: the GPU work")
print("(JOINs and aggregations) produces similar output sizes,")
print("even though the input data is 4x larger.")
print("="*70)
