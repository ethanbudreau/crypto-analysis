#!/usr/bin/env python3
"""
Baseline validation of datasets and query results.
"""
import duckdb
import os

datasets = ['100k', '1m', '5m', '20m']

print("="*80)
print("BASELINE VALIDATION")
print("="*80)

# Part 1: Dataset scaling
print("\n" + "="*80)
print("PART 1: DATASET SCALING VALIDATION")
print("="*80)

dataset_stats = {}
for dataset in datasets:
    nodes_file = f'data/processed/nodes_{dataset}.csv'
    edges_file = f'data/processed/edges_{dataset}.csv'

    # File sizes
    nodes_size_mb = os.path.getsize(nodes_file) / (1024**2)
    edges_size_mb = os.path.getsize(edges_file) / (1024**2)

    # Row counts
    conn = duckdb.connect(':memory:')
    conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}')")
    conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}')")

    node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    illicit_count = conn.execute("SELECT COUNT(*) FROM nodes WHERE class = '1'").fetchone()[0]
    illicit_pct = (illicit_count / node_count * 100) if node_count > 0 else 0

    dataset_stats[dataset] = {
        'nodes_mb': nodes_size_mb,
        'edges_mb': edges_size_mb,
        'node_count': node_count,
        'edge_count': edge_count,
        'illicit_count': illicit_count,
        'illicit_pct': illicit_pct
    }

    print(f"\n{dataset}:")
    print(f"  Nodes: {node_count:,} ({nodes_size_mb:.1f} MB)")
    print(f"  Edges: {edge_count:,} ({edges_size_mb:.1f} MB)")
    print(f"  Illicit: {illicit_count:,} ({illicit_pct:.2f}%)")

    conn.close()

# Check scaling ratios
print("\n" + "-"*80)
print("SCALING RATIOS (vs 100k baseline):")
print("-"*80)
baseline = dataset_stats['100k']
for dataset in ['1m', '5m', '20m']:
    stats = dataset_stats[dataset]
    node_ratio = stats['node_count'] / baseline['node_count']
    edge_ratio = stats['edge_count'] / baseline['edge_count']
    illicit_ratio = stats['illicit_count'] / baseline['illicit_count']

    print(f"\n{dataset}:")
    print(f"  Nodes: {node_ratio:.2f}x")
    print(f"  Edges: {edge_ratio:.2f}x")
    print(f"  Illicit: {illicit_ratio:.2f}x")

    # Check if scaling is consistent
    if abs(node_ratio - edge_ratio) > 0.5:
        print(f"  ⚠️  WARNING: Node/edge scaling mismatch!")
    if abs(stats['illicit_pct'] - baseline['illicit_pct']) > 0.5:
        print(f"  ⚠️  WARNING: Illicit percentage differs from baseline!")

# Part 2: Query result validation
print("\n" + "="*80)
print("PART 2: QUERY RESULT VALIDATION")
print("="*80)
print("Running k_hop query on each dataset and checking result counts...")

for dataset in datasets:
    print(f"\n{dataset}:")
    print("-"*80)

    conn = duckdb.connect(':memory:')
    nodes_file = f'data/processed/nodes_{dataset}.csv'
    edges_file = f'data/processed/edges_{dataset}.csv'

    conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}')")
    conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}')")

    # Load query
    with open('sql/duckdb/k_hop_gpu.sql', 'r') as f:
        lines = [line for line in f.readlines() if not line.strip().startswith('--')]
        query = ''.join(lines).strip().rstrip(';')

    # Run query and count results
    result = conn.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()
    row_count = result[0]

    # Also get breakdown by hop distance
    result = conn.execute(f"""
        SELECT hop_distance, COUNT(*) as count
        FROM ({query})
        GROUP BY hop_distance
        ORDER BY hop_distance
    """).fetchall()

    print(f"  Total results: {row_count:,}")
    print(f"  Breakdown by hop:")
    for hop, count in result:
        print(f"    {hop}-hop: {count:,}")

    conn.close()

print("\n" + "="*80)
print("VALIDATION COMPLETE")
print("="*80)
