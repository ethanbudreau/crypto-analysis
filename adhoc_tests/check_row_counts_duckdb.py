#!/usr/bin/env python3
"""
Check row counts using DuckDB (CPU) - more stable than Sirius CLI
"""
import duckdb

print("="*60)
print("ROW COUNT ANALYSIS (using DuckDB)")
print("="*60)

conn = duckdb.connect(':memory:')

# Load data
print("\nLoading data...")
conn.execute("CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_20m.csv')")
conn.execute("CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_20m.csv')")
print("✅ Data loaded")

# 2-hop count
print("\n" + "="*60)
print("Counting 2-hop results...")
print("="*60)
result = conn.execute("""
SELECT COUNT(*) as row_count FROM (
  SELECT e2.txId2 AS connected_node, MAX(n3.class) AS node_class
  FROM nodes n1
  JOIN edges e1 ON n1.txId = e1.txId1
  JOIN nodes n2 ON e1.txId2 = n2.txId
  JOIN edges e2 ON n2.txId = e2.txId1
  JOIN nodes n3 ON e2.txId2 = n3.txId
  WHERE n1.class = '1' AND e2.txId2 != n1.txId
  GROUP BY e2.txId2
)
""").fetchone()
count_2hop = result[0]
print(f"✅ 2-hop: {count_2hop:,} rows")

# 3-hop count
print("\n" + "="*60)
print("Counting 3-hop results...")
print("="*60)
result = conn.execute("""
SELECT COUNT(*) as row_count FROM (
  SELECT e3.txId2 AS node_id, MAX(n4.class) AS node_class
  FROM nodes n1
  JOIN edges e1 ON n1.txId = e1.txId1
  JOIN nodes n2 ON e1.txId2 = n2.txId
  JOIN edges e2 ON n2.txId = e2.txId1
  JOIN nodes n3 ON e2.txId2 = n3.txId
  JOIN edges e3 ON n3.txId = e3.txId1
  JOIN nodes n4 ON e3.txId2 = n4.txId
  WHERE n1.class = '1' AND e3.txId2 != n1.txId AND e3.txId2 != n2.txId
  GROUP BY e3.txId2
)
""").fetchone()
count_3hop = result[0]
print(f"✅ 3-hop: {count_3hop:,} rows")

conn.close()

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"2-hop: {count_2hop:,} rows")
print(f"3-hop: {count_3hop:,} rows")

if count_3hop > 0:
    ratio = count_2hop / count_3hop
    print(f"\n2-hop returns {ratio:.2f}x more rows than 3-hop")

    if ratio > 1:
        print("\n💡 This explains why 3-hop is faster:")
        print(f"   - 2-hop: {count_2hop:,} rows to GROUP BY and ORDER BY")
        print(f"   - 3-hop: {count_3hop:,} rows to GROUP BY and ORDER BY")
        print("   - Cycle detection (e3.txId2 != n1.txId AND != n2.txId) filters many paths")
        print("   - Less output data = faster final aggregation and sorting")
