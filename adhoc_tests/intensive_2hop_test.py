#!/usr/bin/env python3
"""
Intensive 2-hop query test on Sirius GPU
Run 10,000 sequential queries to verify result materialization
"""

import sys
import time
from pathlib import Path
import importlib.util

# Import benchmark function from 02_run_benchmarks.py
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
spec = importlib.util.spec_from_file_location("run_benchmarks",
                                                str(Path(__file__).parent.parent / "scripts" / "02_run_benchmarks.py"))
run_benchmarks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_benchmarks)
run_sirius_benchmark = run_benchmarks.run_sirius_benchmark

def main():
    print("=" * 80)
    print("INTENSIVE 2-HOP QUERY TEST - SIRIUS GPU")
    print("=" * 80)
    print("Dataset: 5m edges")
    print("Query: 2_hop")
    print("Session queries: 10,000")
    print("=" * 80)
    print()

    start_time = time.time()

    result = run_sirius_benchmark(
        dataset_size='5m',
        query_name='2_hop',
        num_runs=1,
        mode='persistent_session',
        session_queries=10000
    )

    elapsed = time.time() - start_time

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    if result:
        print(f"Total time: {elapsed:.2f}s")
        if 'avg_query_time' in result:
            print(f"Average per query: {result['avg_query_time']:.4f}s")
            print(f"Result row count: {result.get('result_row_count', 'N/A')}")
        print()
        print("Full results:")
        for key, value in sorted(result.items()):
            print(f"  {key}: {value}")
    else:
        print("FAILED - No results returned")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
