.timer on

-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_full_slim.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_full_slim.csv');

-- Initialize GPU
call gpu_buffer_init('256 MB', '512 MB');

-- Test 1: Simple COUNT (should work on GPU)
call gpu_processing('SELECT COUNT(*) FROM edges');

-- Test 2: Simple aggregation with GROUP BY
call gpu_processing('SELECT COUNT(*) FROM edges GROUP BY txId1');

-- Test 3: Simple filter
call gpu_processing('SELECT * FROM edges WHERE txId1 > 1000000 LIMIT 10');

-- Test 4: Simple join without ORDER BY or DISTINCT
call gpu_processing('SELECT n.txId, e.txId2 FROM nodes n JOIN edges e ON n.txId = e.txId1 WHERE n.class = ''1'' LIMIT 10');
