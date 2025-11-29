#!/usr/bin/env python3
"""
Generate and dump the exact SQL script that the benchmark runs.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from run_persistent_session_benchmarks import run_duckdb_benchmark, run_sirius_benchmark

# Read the actual k_hop query
with open('sql/sirius/k_hop_gpu.sql', 'r') as f:
    content = f.read()
    # Remove comment lines
    lines = [line for line in content.split('\n') if not line.strip().startswith('--')]
    clean_query = '\n'.join(lines).strip().rstrip(';')

dataset_size = '5m'
buffer_min, buffer_max = '4 GB', '8 GB'
session_queries = 5  # Just 5 for readability
nodes_file = f'data/processed/nodes_{dataset_size}.csv'
edges_file = f'data/processed/edges_{dataset_size}.csv'

# Build the script exactly as the benchmark does
escaped_query = clean_query.replace("'", "''")

session_script = f"""
-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');

-- Initialize GPU
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

-- Warm-up query (discarded)
call gpu_processing('{escaped_query}');
"""

# Append sequential queries
for i in range(session_queries):
    session_script += f"\n-- Session query {i+1}\ncall gpu_processing('{escaped_query}');\n"

print("="*70)
print("BENCHMARK SCRIPT (what actually runs in Sirius)")
print("="*70)
print(session_script)
print("="*70)
