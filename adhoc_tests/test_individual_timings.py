#!/usr/bin/env python3
"""
Test 2: Run 100 queries with individual timing to check for performance degradation.
"""
import subprocess
import tempfile
import os
import time
import re

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

# Build script with labeled queries
escaped_query = clean_query.replace("'", "''")

session_script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

.timer on
"""

# Add warmup
session_script += f""".print '=== WARMUP ==='
call gpu_processing('{escaped_query}');

"""

# Add 100 individually labeled queries
for i in range(session_queries):
    session_script += f""".print '=== QUERY {i+1} ==='
call gpu_processing('{escaped_query}');

"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
    f.write(session_script)
    temp_file = f.name

try:
    print("="*70)
    print("TEST 2: Individual query timing analysis")
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
    print()

    # Parse individual timings
    lines = result.stdout.split('\n')
    query_times = []
    current_query = None

    for i, line in enumerate(lines):
        if '=== QUERY' in line:
            match = re.search(r'QUERY (\d+)', line)
            if match:
                current_query = int(match.group(1))
        elif 'Run Time' in line and current_query is not None:
            # Extract the real time
            match = re.search(r'real ([\d.]+)', line)
            if match:
                query_times.append({
                    'query_num': current_query,
                    'time': float(match.group(1))
                })
                current_query = None

    if query_times:
        print(f"Successfully parsed {len(query_times)} query timings")
        print()

        # Show first 10, middle 10, last 10
        print("First 10 queries:")
        for qt in query_times[:10]:
            print(f"  Query {qt['query_num']:3d}: {qt['time']:.4f}s")

        if len(query_times) > 20:
            print("\nMiddle 10 queries:")
            mid = len(query_times) // 2
            for qt in query_times[mid-5:mid+5]:
                print(f"  Query {qt['query_num']:3d}: {qt['time']:.4f}s")

        print("\nLast 10 queries:")
        for qt in query_times[-10:]:
            print(f"  Query {qt['query_num']:3d}: {qt['time']:.4f}s")

        # Statistics
        times = [qt['time'] for qt in query_times]
        avg = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\n{'='*70}")
        print("STATISTICS")
        print('='*70)
        print(f"Average: {avg:.4f}s")
        print(f"Min:     {min_time:.4f}s (query {query_times[times.index(min_time)]['query_num']})")
        print(f"Max:     {max_time:.4f}s (query {query_times[times.index(max_time)]['query_num']})")

        # Check for degradation
        first_10_avg = sum(times[:10]) / 10
        last_10_avg = sum(times[-10:]) / 10
        print(f"\nFirst 10 avg: {first_10_avg:.4f}s")
        print(f"Last 10 avg:  {last_10_avg:.4f}s")

        if last_10_avg > first_10_avg * 1.1:
            print(f"⚠️  Performance degraded by {(last_10_avg/first_10_avg - 1)*100:.1f}%")
        elif last_10_avg < first_10_avg * 0.9:
            print(f"✓ Performance improved by {(1 - last_10_avg/first_10_avg)*100:.1f}%")
        else:
            print(f"✓ Performance stable (within 10%)")

    else:
        print("❌ Failed to parse query timings")
        print("\nSample output:")
        print('\n'.join(lines[:50]))

finally:
    if os.path.exists(temp_file):
        os.remove(temp_file)

print("\n" + "="*70)
