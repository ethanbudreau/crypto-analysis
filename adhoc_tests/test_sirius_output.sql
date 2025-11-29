-- Test script to see Sirius timing output
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_full_slim.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_full_slim.csv');

-- Initialize GPU
call gpu_buffer_init('256 MB', '512 MB');

-- Run a simple query
call gpu_processing('SELECT COUNT(*) FROM edges WHERE class = 1');

-- Run it again
call gpu_processing('SELECT COUNT(*) FROM edges WHERE class = 1');
