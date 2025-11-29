#!/usr/bin/env python3
"""
Check number of illicit nodes (class='1') in each dataset.
This could explain why GPU times don't scale with dataset size.
"""
import duckdb

datasets = ['100k', '1m', '5m', '20m']

print("="*60)
print("ILLICIT NODE COUNT BY DATASET")
print("="*60)

for dataset in datasets:
    conn = duckdb.connect(':memory:')

    try:
        # Load nodes
        conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_{dataset}.csv')")

        # Count total and illicit nodes
        total = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        illicit = conn.execute("SELECT COUNT(*) FROM nodes WHERE class = '1'").fetchone()[0]
        pct = (illicit / total * 100) if total > 0 else 0

        print(f"{dataset:5s}: {total:,} total | {illicit:,} illicit ({pct:.2f}%)")

    except Exception as e:
        print(f"{dataset:5s}: Error - {e}")
    finally:
        conn.close()

print("="*60)
print("\nIf illicit counts are similar across datasets, that would")
print("explain why GPU query times don't scale with dataset size:")
print("The queries all start from class='1' nodes, so fewer")
print("illicit seeds = less work regardless of total graph size.")
print("="*60)
