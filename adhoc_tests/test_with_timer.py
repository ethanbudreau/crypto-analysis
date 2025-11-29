#!/usr/bin/env python3
"""
Test 1: Run benchmark WITH .timer on to see if it affects performance.
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

# Build script WITH .timer on
escaped_query = clean_query.replace("'", "''")

session_script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

.timer on

-- Warmup
call gpu_processing('{escaped_query}');
"""

for i in range(session_queries):
    session_script += f"\ncall gpu_processing('{escaped_query}');\n"

with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
    f.write(session_script)
    temp_file = f.name

try:
    print("="*70)
    print("TEST 1: Benchmark WITH .timer on")
    print("="*70)
    print(f"Running {session_queries} queries on {dataset_size} dataset...")
    print()

    total_start = time.time()
    result = subprocess.run(
        [sirius_binary, "-init", temp_file],
        capture_output=True,
        text=True,
        timeout=600
    )
    total_time = time.time() - total_start

    print(f"Total wall time: {total_time:.2f}s")
    print(f"Per query average: {total_time / (session_queries + 1):.3f}s")
    print()

    # Count fallback messages
    fallback_count = result.stdout.count("Error in GPUExecuteQuery")
    print(f"GPU fallback messages: {fallback_count}")

    # Extract some timing lines
    print("\nSample timing lines:")
    lines = result.stdout.split('\n')
    timing_lines = [line for line in lines if 'Run Time' in line]
    if len(timing_lines) > 0:
        print(f"  First: {timing_lines[0]}")
        if len(timing_lines) > 50:
            print(f"  50th:  {timing_lines[49]}")
        if len(timing_lines) > 100:
            print(f"  Last:  {timing_lines[-1]}")

finally:
    if os.path.exists(temp_file):
        os.remove(temp_file)

print("\n" + "="*70)
