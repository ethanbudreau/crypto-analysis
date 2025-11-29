#!/usr/bin/env python3
"""
Test if .timer adds significant overhead to DuckDB execution.
"""
import duckdb
import time

# Read query
with open('sql/duckdb/k_hop_gpu.sql', 'r') as f:
    lines = [line for line in f.readlines() if not line.strip().startswith('--')]
    clean_query = '\n'.join(lines).strip().rstrip(';')

dataset_size = '5m'
nodes_file = f'data/processed/nodes_{dataset_size}.csv'
edges_file = f'data/processed/edges_{dataset_size}.csv'

def run_duckdb_test(use_timer, num_queries=10):
    """Run DuckDB with or without .timer"""

    script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');

{'.timer on' if use_timer else '-- no timer'}
"""

    for i in range(num_queries):
        script += f"\n{clean_query};\n"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(script)
        temp_file = f.name

    try:
        total_start = time.time()
        result = subprocess.run(
            [duckdb_binary, "-init", temp_file],
            capture_output=True,
            text=True,
            timeout=300
        )
        total_time = time.time() - total_start

        return total_time, result.returncode == 0

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

print("="*70)
print("TESTING .timer OVERHEAD IN DUCKDB")
print("="*70)
print(f"Dataset: {dataset_size}")
print()

# Test WITHOUT timer
print("Running 10 queries WITHOUT .timer...")
time_no_timer, success = run_duckdb_test(use_timer=False, num_queries=10)
if success:
    print(f"  Total: {time_no_timer:.2f}s")
    print(f"  Per query: {time_no_timer / 10:.3f}s")
else:
    print(f"  Failed!")

print()

# Test WITH timer
print("Running 10 queries WITH .timer...")
time_with_timer, success = run_duckdb_test(use_timer=True, num_queries=10)
if success:
    print(f"  Total: {time_with_timer:.2f}s")
    print(f"  Per query: {time_with_timer / 10:.3f}s")
else:
    print(f"  Failed!")

print()
print("="*70)
if time_no_timer > 0:
    overhead = (time_with_timer - time_no_timer) / time_no_timer * 100
    print(f".timer overhead: {overhead:.1f}%")
    print(f"Slowdown factor: {time_with_timer / time_no_timer:.2f}x")
print("="*70)
