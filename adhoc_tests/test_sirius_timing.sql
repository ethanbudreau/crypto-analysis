-- Test script to see if Sirius provides timing output
.timer on

-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_full_slim.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_full_slim.csv');

-- Initialize GPU
call gpu_buffer_init('256 MB', '512 MB');

-- Run actual 1-hop query
call gpu_processing('SELECT DISTINCT e.txId2 AS connected_node, n2.class AS node_class FROM nodes n1 JOIN edges e ON n1.txId = e.txId1 JOIN nodes n2 ON e.txId2 = n2.txId WHERE n1.class = ''1'' ORDER BY e.txId2');

-- Run it again to measure warm cache
call gpu_processing('SELECT DISTINCT e.txId2 AS connected_node, n2.class AS node_class FROM nodes n1 JOIN edges e ON n1.txId = e.txId1 JOIN nodes n2 ON e.txId2 = n2.txId WHERE n1.class = ''1'' ORDER BY e.txId2');
