#!/usr/bin/env python3
"""
Verify that datasets are actually different sizes.
"""
import duckdb

datasets = ['5m', '20m']

print("="*60)
print("DATASET SIZE VERIFICATION")
print("="*60)

for dataset in datasets:
    conn = duckdb.connect(':memory:')

    print(f"\n{dataset}:")
    print("-"*60)

    # Load and count
    conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_{dataset}.csv')")
    conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_{dataset}.csv')")

    node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    illicit_count = conn.execute("SELECT COUNT(*) FROM nodes WHERE class = '1'").fetchone()[0]

    print(f"  Nodes:        {node_count:,}")
    print(f"  Edges:        {edge_count:,}")
    print(f"  Illicit:      {illicit_count:,}")

    # Check a few edges starting from illicit nodes
    print(f"\n  Sample edges from illicit nodes:")
    result = conn.execute("""
        SELECT COUNT(*)
        FROM nodes n1
        JOIN edges e1 ON n1.txId = e1.txId1
        WHERE n1.class = '1'
    """).fetchone()
    print(f"    1-hop edges from illicit: {result[0]:,}")

    conn.close()

print("\n" + "="*60)
