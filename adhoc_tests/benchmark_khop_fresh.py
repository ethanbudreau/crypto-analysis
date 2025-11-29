#!/usr/bin/env python3
"""
Fresh k-hop and shortest_path benchmark with proper error capture.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import importlib.util
spec = importlib.util.spec_from_file_location("run_benchmarks", "scripts/02_run_benchmarks.py")
run_benchmarks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_benchmarks)

import csv
from datetime import datetime

DATASETS = ['5m', '20m']
QUERIES = ['k_hop_gpu', 'shortest_path_gpu']
SESSION_QUERIES = 100

print("="*80)
print("FRESH K-HOP AND SHORTEST PATH BENCHMARK")
print("="*80)
print(f"Datasets: {', '.join(DATASETS)}")
print(f"Queries: {', '.join(QUERIES)}")
print(f"Session queries: {SESSION_QUERIES}")
print("="*80)

results = []
total_tests = len(DATASETS) * len(QUERIES) * 2
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

        result = run_benchmarks.run_duckdb_benchmark(
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

        result = run_benchmarks.run_sirius_benchmark(
            dataset_size=dataset,
            query_name=query,
            mode='persistent_session',
            session_queries=SESSION_QUERIES
        )

        if result and result.get('avg_query_time'):
            results.append(result)
            total_time = result.get('total_time', 0)
            avg_time = result['avg_query_time']
            print(f"✅ GPU: {avg_time:.4f}s avg | Total: {total_time:.2f}s")
        else:
            print(f"❌ Failed")
            if result:
                print(f"   Result: {result}")

# Save results
output_dir = 'results/adhoc_benchmarks'
os.makedirs(output_dir, exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = f'{output_dir}/khop_fresh_{timestamp}.csv'

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
            cpu_total = duckdb_result.get('total_time', 0)
            gpu_time = sirius_result.get('avg_query_time', 0)
            gpu_total = sirius_result.get('total_time', 0)

            if gpu_time > 0:
                speedup = cpu_time / gpu_time
                winner = "GPU" if speedup > 1 else "CPU"

                print(f"\n{dataset} | {query}")
                print(f"  CPU: {cpu_time:.4f}s avg ({cpu_total:.2f}s total)")
                print(f"  GPU: {gpu_time:.4f}s avg ({gpu_total:.2f}s total)")
                print(f"  Speedup: {speedup:.2f}x {winner}")

print("\n" + "="*80)
