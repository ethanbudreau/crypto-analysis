-- 1-hop Reachability Query (DuckDB)
-- Find all transactions directly connected to known illicit nodes
--
-- This query identifies transactions that are one step away from
-- confirmed illicit activity, useful for immediate fraud detection.

SELECT DISTINCT
    e.txId2 AS connected_node,
    n2.class AS node_class
FROM nodes n1
JOIN edges e ON n1.txId = e.txId1
JOIN nodes n2 ON e.txId2 = n2.txId
WHERE n1.class = '1'  -- '1' indicates illicit transactions
ORDER BY e.txId2;

-- TODO: Optimize query performance
-- TODO: Add node feature aggregation if needed
-- TODO: Consider indexing strategy
