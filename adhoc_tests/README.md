# Adhoc Tests

This directory contains reference test scripts and SQL files used during development and debugging.

## Reference Scripts

- **graph_connectivity_analysis.py** - Analyzes graph connectivity and reachability
- **intensive_2hop_test.py** - Intensive testing of 2-hop queries
- **test_varied_queries.py** - Testing query variation patterns for benchmarking
- **test_individual_timings.py** - Individual query timing analysis
- **test_with_timer.py** - Timer overhead testing

## Reference SQL Files

### GPU Testing
- **test_gpu_compatible.sql** - Simple GPU-compatible queries
- **test_simple_gpu.sql** - Basic GPU query tests
- **test_fallback_causes.sql** - Queries that trigger GPU fallback

### Baseline Tests
- **test_2hop_baseline.sql** - 2-hop query baseline
- **test_3hop_baseline.sql** - 3-hop query baseline (Note: 3-hop causes GPU issues)

### UNION ALL Testing
- **test_union_all.sql** - Basic UNION ALL test
- **test_union_fallback_scope.sql** - Testing UNION ALL GPU fallback behavior

### Output Testing
- **test_sirius_output.sql** - Sirius output format testing
- **test_sirius_timing.sql** - Sirius timing tests

## Notes

- 3-hop queries are excluded from GPU benchmarks due to segfaults
- Constant columns (e.g., `3 AS hop_distance`) cause GPU fallback
- For production benchmarks, use `/scripts/run_persistent_session_benchmarks.py`
