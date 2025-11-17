-- k-hop Traversal Query (GPU-COMPATIBLE VERSION)
-- Find all transactions within k steps (up to 4 hops) from known illicit nodes
--
-- CHANGES FROM RECURSIVE CTE VERSION:
-- - Removed recursive CTE (causes GPU fallback)
-- - Using UNION of explicit 1-hop, 2-hop, 3-hop, 4-hop queries
-- - Removed DISTINCT, using GROUP BY instead
-- - Removed path tracking (too complex for GPU)
-- - This version RUNS ON GPU

-- 1-hop nodes
SELECT
    e1.txId2 AS node_id,
    MAX(n2.class) AS node_class,
    1 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
WHERE n1.class = '1'
GROUP BY e1.txId2

UNION ALL

-- 2-hop nodes
SELECT
    e2.txId2 AS node_id,
    MAX(n3.class) AS node_class,
    2 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
WHERE n1.class = '1'
  AND e2.txId2 != n1.txId  -- Avoid returning to source
GROUP BY e2.txId2

UNION ALL

-- 3-hop nodes
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
WHERE n1.class = '1'
  AND e3.txId2 != n1.txId  -- Avoid returning to source
  AND e3.txId2 != n2.txId  -- Avoid simple cycles
GROUP BY e3.txId2

UNION ALL

-- 4-hop nodes
SELECT
    e4.txId2 AS node_id,
    MAX(n5.class) AS node_class,
    4 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
JOIN edges e3 ON n3.txId = e3.txId1
JOIN nodes n4 ON e3.txId2 = n4.txId
JOIN edges e4 ON n4.txId = e4.txId1
JOIN nodes n5 ON e4.txId2 = n5.txId
WHERE n1.class = '1'
  AND e4.txId2 != n1.txId  -- Avoid returning to source
  AND e4.txId2 != n2.txId  -- Avoid simple cycles
  AND e4.txId2 != n3.txId  -- Avoid simple cycles
GROUP BY e4.txId2

ORDER BY hop_distance, node_id;

-- EXECUTION NOTES:
-- This simplified non-recursive version is GPU-compatible.
-- Using UNION ALL to combine results from different hop distances.
-- For true recursive traversal with arbitrary k and full cycle detection, use CPU version.
-- This query is verified to avoid "Error in GPUExecuteQuery, fallback to DuckDB".
--
-- Manual execution in Sirius CLI:
--   call gpu_buffer_init('1 GB', '2 GB');
--   call gpu_processing('SELECT e1.txId2 AS node_id...');
