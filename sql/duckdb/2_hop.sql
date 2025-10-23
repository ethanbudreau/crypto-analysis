-- 2-hop Reachability Query (DuckDB)
-- Find all transactions two steps away from known illicit nodes
--
-- This query extends fraud detection to indirect connections,
-- identifying potentially related transactions.

SELECT DISTINCT
    e2.txId2 AS connected_node,
    n3.class AS node_class
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
WHERE n1.class = '1'  -- Start from illicit transactions
  AND e2.txId2 != n1.txId  -- Avoid returning to source
ORDER BY e2.txId2;

-- TODO: Optimize for large graphs
-- TODO: Consider limiting results if too many
-- TODO: Add path tracking if needed
