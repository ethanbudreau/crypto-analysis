#!/usr/bin/env python3
"""
Run EXACTLY what the benchmark does: 100 queries with captured output.
"""
import subprocess
import tempfile
import os
import time

sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")

# Read query
with open('sql/sirius/k_hop_gpu.sql', 'r') as f:
    lines = [line for line in f.readlines() if not line.strip().startswith('--')]
    clean_query = '\n'.join(lines).strip().rstrip(';')

dataset_size = '5m'
buffer_min, buffer_max = '4 GB', '8 GB'
session_queries = 100
nodes_file = f'data/processed/nodes_{dataset_size}.csv'
edges_file = f'data/processed/edges_{dataset_size}.csv'

# Build script
escaped_query = clean_query.replace("'", "''")

session_script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');
call gpu_buffer_init('{buffer_min}', '{buffer_max}');
call gpu_processing('{escaped_query}');
"""

for i in range(session_queries):
    session_script += f"\ncall gpu_processing('{escaped_query}');\n"

with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
    f.write(session_script)
    temp_file = f.name

try:
    print(f"Running {session_queries} queries with captured output...")
    total_start = time.time()
    result = subprocess.run(
        [sirius_binary, "-init", temp_file],
        capture_output=True,  # Like the benchmark does
        text=True,
        timeout=600
    )
    total_time = time.time() - total_start

    print(f"Total time: {total_time:.2f}s")
    print(f"Per query (simple average): {total_time / (session_queries + 1):.3f}s")

    # Check for fallback messages
    fallback_count = result.stdout.count("Error in GPUExecuteQuery")
    print(f"GPU fallback messages: {fallback_count}")

finally:
    if os.path.exists(temp_file):
        os.remove(temp_file)
