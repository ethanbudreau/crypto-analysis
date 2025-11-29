.timer on

CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_20m.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_20m.csv');

call gpu_buffer_init('4 GB', '6 GB');

call gpu_processing('
SELECT
    e2.txId2 AS node_id,
    MAX(n3.class) AS node_class,
    2 AS hop_distance
FROM nodes n1
JOIN edges e1 ON n1.txId = e1.txId1
JOIN nodes n2 ON e1.txId2 = n2.txId
JOIN edges e2 ON n2.txId = e2.txId1
JOIN nodes n3 ON e2.txId2 = n3.txId
WHERE n1.class = ''1''
  AND e2.txId2 != n1.txId
GROUP BY e2.txId2
');
