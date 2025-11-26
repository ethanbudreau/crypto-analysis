.timer on

-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_full_slim.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_full_slim.csv');

-- Initialize GPU
call gpu_buffer_init('256 MB', '512 MB');

-- Test GPU-compatible 1-hop query (using GROUP BY instead of DISTINCT)
call gpu_processing('SELECT e.txId2 AS connected_node, MAX(n2.class) AS node_class FROM nodes n1 JOIN edges e ON n1.txId = e.txId1 JOIN nodes n2 ON e.txId2 = n2.txId WHERE n1.class = ''1'' GROUP BY e.txId2 ORDER BY e.txId2');
