#!/usr/bin/env python3
"""
Test when query performance stabilizes by running multiple batches.
"""

import sys
sys.path.insert(0, 'scripts')
from importlib import util
spec = util.spec_from_file_location('run_benchmarks', 'scripts/02_run_benchmarks.py')
run_benchmarks = util.module_from_spec(spec)
spec.loader.exec_module(run_benchmarks)

print('Query Timing Stability Test')
print('=' * 60)
print('Running 10 batches of 10 queries each on 20m 3_hop')
print('This shows when performance stabilizes\n')

# Run 10 batches of 10 queries
batch_results = []

for batch in range(10):
    print(f'\nBatch {batch+1}/10:')

    # DuckDB
    result_duckdb = run_benchmarks.run_duckdb_benchmark(
        dataset_size='20m',
        query_name='3_hop',
        mode='persistent_session',
        session_queries=10
    )

    # Sirius
    result_sirius = run_benchmarks.run_sirius_benchmark(
        dataset_size='20m',
        query_name='3_hop',
        mode='persistent_session',
        session_queries=10
    )

    if result_duckdb and result_sirius:
        batch_results.append({
            'batch': batch + 1,
            'duckdb_avg': result_duckdb['avg_query_time'],
            'sirius_avg': result_sirius['avg_query_time']
        })
        print(f'  DuckDB: {result_duckdb["avg_query_time"]:.4f}s')
        print(f'  Sirius: {result_sirius["avg_query_time"]:.4f}s')

print('\n' + '=' * 60)
print('Summary across batches:')
print(f'{"Batch":>6} | {"DuckDB Avg":>11} | {"Sirius Avg":>11} | {"Speedup":>8}')
print('-' * 60)
for r in batch_results:
    speedup = r['duckdb_avg'] / r['sirius_avg'] if r['sirius_avg'] > 0 else 0
    print(f'{r["batch"]:>6} | {r["duckdb_avg"]:>11.4f}s | {r["sirius_avg"]:>11.4f}s | {speedup:>8.2f}x')

if batch_results:
    avg_duckdb = sum(r['duckdb_avg'] for r in batch_results) / len(batch_results)
    avg_sirius = sum(r['sirius_avg'] for r in batch_results) / len(batch_results)
    print('-' * 60)
    print(f'{"Mean":>6} | {avg_duckdb:>11.4f}s | {avg_sirius:>11.4f}s | {avg_duckdb/avg_sirius:>8.2f}x')
