#!/usr/bin/env python3
"""
Test UNION ALL fallback using the same methodology as benchmarks.
This avoids CLI crashes by using subprocess approach.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from run_persistent_session_benchmarks import run_sirius_benchmark

print("="*80)
print("UNION ALL FALLBACK TEST - Using Benchmark Methodology")
print("="*80)

# Test 1: 2-hop baseline
print("\n[1/3] Testing 2-hop baseline (GPU)...")
result_2hop = run_sirius_benchmark(
    dataset_size='20m',
    query_name='2_hop_gpu',
    mode='persistent_session',
    session_queries=100
)
time_2hop = result_2hop.get('avg_query_time', 0) if result_2hop else 0
print(f"✅ 2-hop: {time_2hop:.4f}s avg (100 queries)")

# Test 2: 3-hop baseline
print("\n[2/3] Testing 3-hop baseline (GPU)...")
result_3hop = run_sirius_benchmark(
    dataset_size='20m',
    query_name='3_hop_gpu',
    mode='persistent_session',
    session_queries=100
)
time_3hop = result_3hop.get('avg_query_time', 0) if result_3hop else 0
print(f"✅ 3-hop: {time_3hop:.4f}s avg (100 queries)")

# Test 3: Check if we have k-hop query (which uses UNION ALL)
print("\n[3/3] Testing k-hop (uses UNION ALL)...")
result_khop = run_sirius_benchmark(
    dataset_size='20m',
    query_name='k_hop_gpu',
    mode='persistent_session',
    session_queries=100
)

if result_khop and result_khop.get('avg_query_time'):
    time_khop = result_khop['avg_query_time']
    print(f"✅ k-hop: {time_khop:.4f}s avg")

    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    print(f"2-hop time:  {time_2hop:.4f}s (GPU)")
    print(f"3-hop time:  {time_3hop:.4f}s (GPU)")
    print(f"k-hop time:  {time_khop:.4f}s (includes 1-4 hop with UNION ALL)")
    print()

    # k-hop includes 1,2,3,4-hop with UNION ALL
    # If partial fallback: should be similar to slowest component
    # If full fallback: should be much slower

    if time_khop < (time_2hop + time_3hop):
        print(f"✓ k-hop ({time_khop:.4f}s) < 2-hop + 3-hop ({time_2hop+time_3hop:.4f}s)")
        print("  → Suggests GPU execution with partial fallback for UNION")
    else:
        print(f"✗ k-hop ({time_khop:.4f}s) ≥ 2-hop + 3-hop ({time_2hop+time_3hop:.4f}s)")
        print("  → Suggests full CPU fallback")

else:
    print(f"❌ k-hop test failed or has error")
    if result_khop:
        print(f"   Error: {result_khop.get('error', 'Unknown')}")

print("\n" + "="*80)
