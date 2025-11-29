-- Test to determine if UNION ALL causes full or partial GPU fallback
-- If the subqueries run on GPU and only UNION runs on CPU, we'd expect:
--   - Similar performance to individual GPU queries
-- If the entire query falls back to CPU, we'd expect:
--   - Much slower performance (similar to pure DuckDB)

.timer on

-- Load data (5M dataset - slim format, won't crash)
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_5m_slim.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_5m_slim.csv');

-- Initialize GPU with maximum memory (8GB GPU total)
call gpu_buffer_init('4 GB', '6 GB');

-- Test 1: Run 2-hop query alone (known GPU query)
.print '=== Test 1: 2-hop alone (GPU baseline) ==='
call gpu_processing('
SELECT
    e2.txId2 AS node_id,
    MAX(n3.class) AS node_class,
    2 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
WHERE n1.class = ''1''
  AND e2.txId2 != n1.txId
GROUP BY e2.txId2
LIMIT 10000
');

-- Test 2: Run 3-hop query alone (known GPU query)
.print '=== Test 2: 3-hop alone (GPU baseline) ==='
call gpu_processing('
SELECT
    e3.txId2 AS node_id,
    MAX(n4.class) AS node_class,
    3 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
JOIN edges e3 ON n3.txId = e3.txId1
JOIN nodes n4 ON e3.txId2 = n4.txId
WHERE n1.class = ''1''
  AND e3.txId2 != n1.txId
  AND e3.txId2 != n2.txId
GROUP BY e3.txId2
LIMIT 10000
');

-- Test 3: UNION ALL of the two queries
.print '=== Test 3: 2-hop UNION ALL 3-hop (test fallback scope) ==='
call gpu_processing('
SELECT
    e2.txId2 AS node_id,
    MAX(n3.class) AS node_class,
    2 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
WHERE n1.class = ''1''
  AND e2.txId2 != n1.txId
GROUP BY e2.txId2

UNION ALL

SELECT
    e3.txId2 AS node_id,
    MAX(n4.class) AS node_class,
    3 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
JOIN edges e3 ON n3.txId = e3.txId1
JOIN nodes n4 ON e3.txId2 = n4.txId
WHERE n1.class = ''1''
  AND e3.txId2 != n1.txId
  AND e3.txId2 != n2.txId
GROUP BY e3.txId2

LIMIT 10000
');

-- Expected results:
-- If PARTIAL fallback (subqueries on GPU, UNION on CPU):
--   Test 3 time ≈ max(Test 1, Test 2) + small overhead
--
-- If FULL fallback (entire query on CPU):
--   Test 3 time >> Test 1 + Test 2 (much slower, all CPU)
