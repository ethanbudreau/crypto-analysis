-- k-hop Traversal Query (DuckDB)
-- Find all transactions within k steps (3-4 hops) from known illicit nodes
--
-- This query performs multi-step graph traversal to identify
-- extended networks of potentially related transactions.
-- Note: This is computationally intensive for large graphs.

-- Using recursive CTE for k-hop traversal (k=3 shown, adjust as needed)
WITH RECURSIVE traversal AS (
    -- Base case: Start with illicit nodes (hop 0)
    SELECT
        n.txId AS node_id,
        n.class AS node_class,
        0 AS hop_distance,
        CAST(n.txId AS VARCHAR) AS path
    FROM nodes n
    WHERE n.class = '1'

    UNION ALL

    -- Recursive case: Add one more hop
    SELECT
        e.txId2 AS node_id,
        n.class AS node_class,
        t.hop_distance + 1 AS hop_distance,
        t.path || '->' || CAST(e.txId2 AS VARCHAR) AS path
    FROM traversal t
    JOIN edges e ON t.node_id = e.txId1
    JOIN nodes n ON e.txId2 = n.txId
    WHERE t.hop_distance < 3  -- Limit to 3 hops (change as needed)
      AND POSITION(CAST(e.txId2 AS VARCHAR) IN t.path) = 0  -- Prevent cycles
)
SELECT DISTINCT
    node_id,
    node_class,
    hop_distance
FROM traversal
WHERE hop_distance > 0  -- Exclude starting nodes
ORDER BY hop_distance, node_id;

-- TODO: Adjust k value (currently 3)
-- TODO: Add performance limits for very large graphs
-- TODO: Consider materialized views for repeated queries
