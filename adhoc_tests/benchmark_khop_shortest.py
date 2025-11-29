#!/usr/bin/env python3
"""
Full benchmark of k-hop and shortest_path queries comparing DuckDB vs Sirius.
These queries use UNION ALL which causes partial GPU fallback.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from run_persistent_session_benchmarks import run_duckdb_benchmark, run_sirius_benchmark
import csv
from datetime import datetime

DATASETS = ['100k', '1m', '5m', '20m']
QUERIES = ['k_hop_gpu', 'shortest_path_gpu']
SESSION_QUERIES = 100

print("="*80)
print("K-HOP AND SHORTEST PATH BENCHMARK")
print("DuckDB (CPU) vs Sirius (GPU with partial UNION ALL fallback)")
print("="*80)
print(f"Datasets: {', '.join(DATASETS)}")
print(f"Queries: {', '.join(QUERIES)}")
print(f"Session queries: {SESSION_QUERIES}")
print("="*80)

results = []
total_tests = len(DATASETS) * len(QUERIES) * 2  # x2 for both databases
current = 0

for dataset in DATASETS:
    print(f"\n{'='*80}")
    print(f"Dataset: {dataset}")
    print('='*80)

    for query in QUERIES:
        # DuckDB
        current += 1
        print(f"\n[{current}/{total_tests}] DuckDB | {dataset} | {query}")
        print("-"*80)

        result = run_duckdb_benchmark(
            dataset_size=dataset,
            query_name=query,
            mode='persistent_session',
            session_queries=SESSION_QUERIES
        )

        if result and result.get('avg_query_time'):
            results.append(result)
            print(f"✅ CPU: {result['avg_query_time']:.4f}s avg")
        else:
            print(f"❌ Failed")

        # Sirius
        current += 1
        print(f"\n[{current}/{total_tests}] Sirius | {dataset} | {query}")
        print("-"*80)

        result = run_sirius_benchmark(
            dataset_size=dataset,
            query_name=query,
            mode='persistent_session',
            session_queries=SESSION_QUERIES
        )

        if result and result.get('avg_query_time'):
            results.append(result)
            print(f"✅ GPU (partial fallback): {result['avg_query_time']:.4f}s avg")
        else:
            print(f"❌ Failed")

# Save results
output_dir = 'results/adhoc_benchmarks'
os.makedirs(output_dir, exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = f'{output_dir}/khop_shortest_path_{timestamp}.csv'

if results:
    fieldnames = sorted(set().union(*[r.keys() for r in results]))
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"\n✅ Results saved to: {output_file}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

successful = [r for r in results if r.get('avg_query_time')]
print(f"Total tests: {total_tests}")
print(f"Successful: {len(successful)}")
print(f"Failed: {total_tests - len(successful)}")

# Compare DuckDB vs Sirius
print("\n" + "-"*80)
print("GPU SPEEDUP ANALYSIS")
print("-"*80)

for dataset in DATASETS:
    for query in QUERIES:
        duckdb_result = next((r for r in results if r.get('database') == 'duckdb'
                             and r.get('dataset_size') == dataset
                             and r.get('query') == query), None)
        sirius_result = next((r for r in results if r.get('database') == 'sirius'
                             and r.get('dataset_size') == dataset
                             and r.get('query') == query), None)

        if duckdb_result and sirius_result:
            cpu_time = duckdb_result.get('avg_query_time', 0)
            gpu_time = sirius_result.get('avg_query_time', 0)

            if gpu_time > 0:
                speedup = cpu_time / gpu_time
                winner = "GPU" if speedup > 1 else "CPU"
                symbol = "🚀" if speedup > 2 else ("✓" if speedup > 1 else "⚠️")

                print(f"{dataset:5s} | {query:20s} | CPU: {cpu_time:7.4f}s | GPU: {gpu_time:7.4f}s | {speedup:5.2f}x {winner} {symbol}")

print("\n" + "="*80)
print("Note: GPU queries use UNION ALL which causes partial CPU fallback,")
print("but the heavy JOINs still run on GPU, providing speedup.")
print("="*80)
