#!/usr/bin/env python3
"""
Run a SINGLE k_hop query on each dataset to see actual timing without session complexity.
"""
import subprocess
import tempfile
import os
import time

sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")

def run_single_query(dataset_size, buffer_min, buffer_max):
    """Run a single k_hop query and time it."""

    # Read the k_hop query
    with open('sql/sirius/k_hop_gpu.sql', 'r') as f:
        lines = [line for line in f.readlines() if not line.strip().startswith('--')]
        query = ''.join(lines).strip().rstrip(';')
        escaped_query = query.replace("'", "''")

    script = f"""
-- Load data
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_{dataset_size}.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_{dataset_size}.csv');

-- Initialize GPU
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

-- Run query and count results
.timer on
call gpu_processing('
    SELECT COUNT(*) as result_count FROM (
        {escaped_query}
    )
');
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(script)
        temp_file = f.name

    try:
        start = time.time()
        result = subprocess.run(
            [sirius_binary, "-init", temp_file],
            capture_output=True,
            text=True,
            timeout=120
        )
        total_time = time.time() - start

        print(f"\n{dataset_size} ({buffer_min}-{buffer_max}):")
        print("-" * 70)
        print(f"Total wall time: {total_time:.3f}s")

        if result.returncode == 0:
            # Look for result count and timing info
            for line in result.stdout.split('\n'):
                if 'result_count' in line or 'Run' in line or '|' in line:
                    print(line)
        else:
            print(f"Error: {result.stderr[:500]}")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

print("="*70)
print("SINGLE K-HOP QUERY TIMING TEST")
print("="*70)

run_single_query('5m', '4 GB', '8 GB')
run_single_query('20m', '6 GB', '8 GB')

print("\n" + "="*70)
