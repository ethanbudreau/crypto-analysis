-- 1-hop Reachability Query (Sirius GPU-accelerated)
-- Find all transactions directly connected to known illicit nodes
--
-- This is the GPU-accelerated version of the 1-hop query using Sirius.
-- Sirius executes DuckDB-compatible SQL on NVIDIA GPUs via libcudf.

SELECT DISTINCT
    e.txId2 AS connected_node,
    n2.class AS node_class
FROM nodes n1
JOIN edges e ON n1.txId = e.txId1
JOIN nodes n2 ON e.txId2 = n2.txId
WHERE n1.class = '1'  -- '1' indicates illicit transactions
ORDER BY e.txId2;

-- EXECUTION NOTES:
-- This query is executed via Sirius's gpu_processing() function.
-- The benchmark script wraps this SQL in gpu_processing() automatically.
--
-- Manual execution in Sirius CLI:
--   call gpu_buffer_init('512 MB', '1 GB');
--   call gpu_processing('SELECT DISTINCT ...');
