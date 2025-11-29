.timer on

-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_full_slim.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_full_slim.csv');

-- Initialize GPU
call gpu_buffer_init('256 MB', '512 MB');

-- Test 1: Join WITHOUT DISTINCT or ORDER BY (should work)
call gpu_processing('SELECT e.txId2, n2.class FROM nodes n1 JOIN edges e ON n1.txId = e.txId1 JOIN nodes n2 ON e.txId2 = n2.txId WHERE n1.class = ''1'' LIMIT 100');

-- Test 2: Same query WITH DISTINCT but no ORDER BY
call gpu_processing('SELECT DISTINCT e.txId2, n2.class FROM nodes n1 JOIN edges e ON n1.txId = e.txId1 JOIN nodes n2 ON e.txId2 = n2.txId WHERE n1.class = ''1''');

-- Test 3: Same query WITH ORDER BY but no DISTINCT
call gpu_processing('SELECT e.txId2, n2.class FROM nodes n1 JOIN edges e ON n1.txId = e.txId1 JOIN nodes n2 ON e.txId2 = n2.txId WHERE n1.class = ''1'' ORDER BY e.txId2 LIMIT 100');

-- Test 4: Full query WITH BOTH DISTINCT and ORDER BY (original query)
call gpu_processing('SELECT DISTINCT e.txId2, n2.class FROM nodes n1 JOIN edges e ON n1.txId = e.txId1 JOIN nodes n2 ON e.txId2 = n2.txId WHERE n1.class = ''1'' ORDER BY e.txId2');
