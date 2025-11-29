#!/usr/bin/env python3
"""
Run 10 sequential queries and try to extract individual timings.
"""
import subprocess
import tempfile
import os

sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")

def test_sequential_timings(dataset_size, buffer_min, buffer_max):
    """Run 10 queries and see individual timings."""

    # Load query
    with open('sql/sirius/k_hop_gpu.sql', 'r') as f:
        lines = [line for line in f.readlines() if not line.strip().startswith('--')]
        query = ''.join(lines).strip().rstrip(';')
        escaped_query = query.replace("'", "''")

    # Build script with timer on
    script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_{dataset_size}.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_{dataset_size}.csv');
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

.timer on
"""

    # Add 10 sequential queries
    for i in range(10):
        script += f""".print 'Query {i+1}:'
call gpu_processing('SELECT COUNT(*) FROM ({escaped_query})');

"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(script)
        temp_file = f.name

    try:
        result = subprocess.run(
            [sirius_binary, "-init", temp_file],
            capture_output=True,
            text=True,
            timeout=180
        )

        print(f"\n{'='*70}")
        print(f"{dataset_size} DATASET - SEQUENTIAL QUERY TIMINGS")
        print('='*70)

        if result.returncode == 0:
            # Extract timings
            output_lines = result.stdout.split('\n')
            for i, line in enumerate(output_lines):
                if 'Query' in line or 'Run Time' in line:
                    print(line)
        else:
            print(f"Error: {result.stderr[:500]}")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

print("="*70)
print("INDIVIDUAL QUERY TIMING ANALYSIS")
print("="*70)
print("Testing if later queries are faster due to caching...")
print("="*70)

test_sequential_timings('5m', '4 GB', '8 GB')
test_sequential_timings('20m', '6 GB', '8 GB')

print("\n" + "="*70)
