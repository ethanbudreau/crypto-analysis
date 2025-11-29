#!/usr/bin/env python3
"""
Query-by-query timing test to see when performance stabilizes.
"""

import sys
import time
import subprocess
import tempfile

sys.path.insert(0, 'scripts')
from importlib import util
spec = util.spec_from_file_location('run_benchmarks', 'scripts/02_run_benchmarks.py')
run_benchmarks = util.module_from_spec(spec)
spec.loader.exec_module(run_benchmarks)

# Load the query
query = run_benchmarks.load_sql_query('sirius', '3_hop')

# Setup
nodes_file = 'data/processed/nodes_20m.csv'
edges_file = 'data/processed/edges_20m.csv'
buffer_size_min = '6 GB'
buffer_size_max = '8 GB'

# Create initialization SQL
init_sql = f"""
call gpu_buffer_init('{buffer_size_min}', '{buffer_size_max}');

CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');
"""

print('Running 100 queries with individual timing...')
print('=' * 60)

# Write init SQL to temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
    f.write(init_sql)
    init_file = f.name

# Initialize database
print('Initializing database...')
init_start = time.time()
result = subprocess.run(
    ['./sirius/build/release/duckdb', '-init', init_file],
    capture_output=True,
    text=True,
    timeout=60
)
init_time = time.time() - init_start
print(f'Initialization: {init_time:.2f}s\n')

# Now run queries individually
timings = []
print('Running queries:')

# Write query to temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
    f.write(init_sql + '\n' + query)
    query_file = f.name

for i in range(100):
    start = time.time()
    result = subprocess.run(
        ['./sirius/build/release/duckdb', '-init', query_file],
        capture_output=True,
        text=True,
        timeout=30
    )
    elapsed = time.time() - start
    timings.append(elapsed)

    if (i + 1) % 10 == 0:
        avg_last_10 = sum(timings[-10:]) / 10
        print(f'  Completed {i+1:3d}/100 queries (last 10 avg: {avg_last_10:.4f}s)')

print('\n' + '=' * 60)
print('Detailed timings:\n')

print('First 20 queries:')
for i in range(20):
    print(f'  Query {i+1:3d}: {timings[i]:.4f}s')

print(f'\nQueries 41-60:')
for i in range(40, 60):
    print(f'  Query {i+1:3d}: {timings[i]:.4f}s')

print(f'\nLast 20 queries:')
for i in range(80, 100):
    print(f'  Query {i+1:3d}: {timings[i]:.4f}s')

print('\n' + '=' * 60)
print('Summary:')
print(f'  First 10 avg:  {sum(timings[0:10])/10:.4f}s')
print(f'  Queries 11-20: {sum(timings[10:20])/10:.4f}s')
print(f'  Queries 21-50: {sum(timings[20:50])/30:.4f}s')
print(f'  Last 50 avg:   {sum(timings[50:100])/50:.4f}s')
print(f'  Overall avg:   {sum(timings)/len(timings):.4f}s')

import os
os.unlink(init_file)
os.unlink(query_file)
