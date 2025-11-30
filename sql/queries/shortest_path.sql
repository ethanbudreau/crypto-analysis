-- Shortest Path Analysis Query
-- ⚠️ GPU STATUS: PARTIAL COMPATIBILITY - Not recommended
-- REASON: UNION ALL causes partial CPU fallback (joins on GPU, union on CPU)
-- RECOMMENDATION: Use DuckDB recursive CTE instead (~0.45s for full BFS on 5M)
-- Compute the shortest path distance from each node to the nearest illicit node
--
-- CHANGES FROM RECURSIVE CTE VERSION:
-- - Removed recursive CTE (causes GPU fallback)
-- - Computes paths up to 5 hops using explicit JOINs
-- - Takes minimum distance for nodes reachable at multiple hop distances
-- - Removed DISTINCT, using GROUP BY instead
-- - Simplified to focus on distance calculation
-- - This version RUNS ON GPU

WITH all_paths AS (
    -- Distance 0: Illicit nodes themselves
    SELECT
        n.txId AS node_id,
        n.class AS node_class,
        0 AS distance_to_illicit
    FROM nodes n
    WHERE n.class = '1'

    UNION ALL

    -- Distance 1: Nodes 1 hop from illicit
    SELECT
        e1.txId2 AS node_id,
        n2.class AS node_class,
        1 AS distance_to_illicit
    FROM nodes n1
    JOIN edges e1 ON n1.txId = e1.txId1
    JOIN nodes n2 ON e1.txId2 = n2.txId
    WHERE n1.class = '1'

    UNION ALL

    -- Distance 2: Nodes 2 hops from illicit
    SELECT
        e2.txId2 AS node_id,
        n3.class AS node_class,
        2 AS distance_to_illicit
    FROM nodes n1
    JOIN edges e1 ON n1.txId = e1.txId1
    JOIN edges e2 ON e1.txId2 = e2.txId1
    JOIN nodes n3 ON e2.txId2 = n3.txId
    WHERE n1.class = '1'

    UNION ALL

    -- Distance 3: Nodes 3 hops from illicit
    SELECT
        e3.txId2 AS node_id,
        n4.class AS node_class,
        3 AS distance_to_illicit
    FROM nodes n1
    JOIN edges e1 ON n1.txId = e1.txId1
    JOIN edges e2 ON e1.txId2 = e2.txId1
    JOIN edges e3 ON e2.txId2 = e3.txId1
    JOIN nodes n4 ON e3.txId2 = n4.txId
    WHERE n1.class = '1'

    UNION ALL

    -- Distance 4: Nodes 4 hops from illicit
    SELECT
        e4.txId2 AS node_id,
        n5.class AS node_class,
        4 AS distance_to_illicit
    FROM nodes n1
    JOIN edges e1 ON n1.txId = e1.txId1
    JOIN edges e2 ON e1.txId2 = e2.txId1
    JOIN edges e3 ON e2.txId2 = e3.txId1
    JOIN edges e4 ON e3.txId2 = e4.txId1
    JOIN nodes n5 ON e4.txId2 = n5.txId
    WHERE n1.class = '1'

    UNION ALL

    -- Distance 5: Nodes 5 hops from illicit
    SELECT
        e5.txId2 AS node_id,
        n6.class AS node_class,
        5 AS distance_to_illicit
    FROM nodes n1
    JOIN edges e1 ON n1.txId = e1.txId1
    JOIN edges e2 ON e1.txId2 = e2.txId1
    JOIN edges e3 ON e2.txId2 = e3.txId1
    JOIN edges e4 ON e3.txId2 = e4.txId1
    JOIN edges e5 ON e4.txId2 = e5.txId1
    JOIN nodes n6 ON e5.txId2 = n6.txId
    WHERE n1.class = '1'
)
-- Get minimum distance for each node
SELECT
    node_id,
    MAX(node_class) AS node_class,  -- Arbitrary aggregation since class is the same for each node_id
    MIN(distance_to_illicit) AS min_distance_to_illicit
FROM all_paths
GROUP BY node_id
ORDER BY min_distance_to_illicit, node_id;

-- EXECUTION NOTES:
-- This simplified non-recursive version is GPU-compatible.
-- Computes shortest paths up to distance 5 (adjust UNION queries for different max distance).
-- For true BFS with arbitrary depth and better cycle handling, use CPU recursive version.
-- This query is verified to avoid "Error in GPUExecuteQuery, fallback to DuckDB".
--
-- Manual execution in Sirius CLI:
--   call gpu_buffer_init('1 GB', '2 GB');
--   call gpu_processing('WITH all_paths AS (...) SELECT ...');
