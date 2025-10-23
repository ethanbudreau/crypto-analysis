-- Shortest Path Analysis Query (DuckDB)
-- Compute the shortest path distance from each node to the nearest illicit node
--
-- This query uses BFS-like traversal to find the minimum number of hops
-- from any transaction to the closest known illicit transaction.

WITH RECURSIVE shortest_path AS (
    -- Base case: Illicit nodes have distance 0 to themselves
    SELECT
        n.txId AS node_id,
        n.txId AS closest_illicit_node,
        0 AS distance_to_illicit,
        CAST(n.txId AS VARCHAR) AS path
    FROM nodes n
    WHERE n.class = '1'

    UNION ALL

    -- Recursive case: BFS traversal
    SELECT
        e.txId2 AS node_id,
        sp.closest_illicit_node,
        sp.distance_to_illicit + 1 AS distance_to_illicit,
        sp.path || '->' || CAST(e.txId2 AS VARCHAR) AS path
    FROM shortest_path sp
    JOIN edges e ON sp.node_id = e.txId1
    WHERE sp.distance_to_illicit < 10  -- Limit search depth
      AND NOT EXISTS (
          -- Only add if we haven't seen this node at a shorter distance
          SELECT 1
          FROM shortest_path sp2
          WHERE sp2.node_id = e.txId2
            AND sp2.distance_to_illicit <= sp.distance_to_illicit
      )
)
-- Get the minimum distance for each node
SELECT
    sp.node_id,
    n.class AS node_class,
    MIN(sp.distance_to_illicit) AS min_distance_to_illicit,
    -- Get the closest illicit node (pick one if multiple)
    (SELECT sp2.closest_illicit_node
     FROM shortest_path sp2
     WHERE sp2.node_id = sp.node_id
       AND sp2.distance_to_illicit = MIN(sp.distance_to_illicit)
     LIMIT 1) AS closest_illicit_node
FROM shortest_path sp
JOIN nodes n ON sp.node_id = n.txId
GROUP BY sp.node_id, n.class
ORDER BY min_distance_to_illicit, sp.node_id;

-- TODO: Optimize for very large graphs
-- TODO: Consider path compression techniques
-- TODO: May need to adjust search depth limit
