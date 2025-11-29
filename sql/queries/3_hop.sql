-- 3-hop Reachability Query (GPU-COMPATIBLE VERSION)
-- Find all transactions three steps away from known illicit nodes
--
-- CHANGES FROM RECURSIVE CTE VERSION:
-- - Removed recursive CTE (may not be GPU-compatible)
-- - Fixed 3-hop traversal using explicit JOINs
-- - Removed DISTINCT, using GROUP BY instead
-- - Removed path tracking and cycle detection (too complex for GPU)
-- - This version RUNS ON GPU

SELECT
    e3.txId2 AS node_id,
    MAX(n4.class) AS node_class,  -- MAX is arbitrary, txId2 is unique per node
    3 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
JOIN edges e3 ON n3.txId = e3.txId1
JOIN nodes n4 ON e3.txId2 = n4.txId
WHERE n1.class = '1'  -- Start from illicit transactions
  AND e3.txId2 != n1.txId  -- Avoid returning to source
  AND e3.txId2 != n2.txId  -- Avoid simple cycles
GROUP BY e3.txId2
ORDER BY e3.txId2;

-- EXECUTION NOTES:
-- This simplified non-recursive version is GPU-compatible.
-- For true k-hop with arbitrary k and full cycle detection, use CPU version.
-- This query is verified to avoid "Error in GPUExecuteQuery, fallback to DuckDB".
--
-- Manual execution in Sirius CLI:
--   call gpu_buffer_init('1 GB', '2 GB');
--   call gpu_processing('SELECT e3.txId2 ...');
