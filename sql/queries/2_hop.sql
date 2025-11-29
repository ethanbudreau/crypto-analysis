-- 2-hop Reachability Query (GPU-COMPATIBLE VERSION)
-- Find all transactions two steps away from known illicit nodes
--
-- CHANGES FROM ORIGINAL:
-- - Removed DISTINCT (causes GPU fallback)
-- - Using GROUP BY instead to ensure unique results
-- - This version RUNS ON GPU

SELECT
    e2.txId2 AS connected_node,
    MAX(n3.class) AS node_class  -- MAX is arbitrary, txId2 is unique per node
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
WHERE n1.class = '1'  -- Start from illicit transactions
  AND e2.txId2 != n1.txId  -- Avoid returning to source
GROUP BY e2.txId2
ORDER BY e2.txId2;

-- EXECUTION NOTES:
-- Multi-hop JOINs benefit significantly from GPU parallelization.
-- This query is GPU-compatible and will execute on NVIDIA GPUs via Sirius.
-- Verified to avoid "Error in GPUExecuteQuery, fallback to DuckDB" message.
--
-- Manual execution in Sirius CLI:
--   call gpu_buffer_init('512 MB', '1 GB');
--   call gpu_processing('SELECT e2.txId2 ...');
