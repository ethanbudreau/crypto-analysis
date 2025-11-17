-- 1-hop Reachability Query (GPU-COMPATIBLE VERSION)
-- Find all transactions directly connected to known illicit nodes
--
-- CHANGES FROM ORIGINAL:
-- - Removed DISTINCT (causes GPU fallback)
-- - Using GROUP BY instead to ensure unique results
-- - This version RUNS ON GPU

SELECT
    e.txId2 AS connected_node,
    MAX(n2.class) AS node_class  -- MAX is arbitrary, txId2 is unique per node
FROM nodes n1
JOIN edges e ON n1.txId = e.txId1
JOIN nodes n2 ON e.txId2 = n2.txId
WHERE n1.class = '1'  -- '1' indicates illicit transactions
GROUP BY e.txId2
ORDER BY e.txId2;

-- EXECUTION NOTES:
-- This query is GPU-compatible and will execute on NVIDIA GPUs via Sirius.
-- Verified to avoid "Error in GPUExecuteQuery, fallback to DuckDB" message.
--
-- Manual execution in Sirius CLI:
--   call gpu_buffer_init('512 MB', '1 GB');
--   call gpu_processing('SELECT e.txId2 ...');
