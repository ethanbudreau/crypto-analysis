# Current Status - GPU Benchmark Project

**Last Updated**: 2025-11-29

## ✅ Completed Work

### 1. GPU Compatibility Discovery ✅
- **Fully GPU-compatible**: `1_hop`, `2_hop` (simple joins, no UNION ALL)
- **Partial GPU acceleration**: `k_hop`, `shortest_path` (joins on GPU, UNION ALL on CPU)
- **Not GPU-compatible**: `3_hop` (causes segmentation faults with 6-table joins)
- **Additional limitation discovered**: Constant literal columns (e.g., `3 AS hop_distance`) cause GPU fallback or hangs

### 2. Benchmark Infrastructure ✅
- Implemented persistent session benchmarking (100 queries per test)
- Added query variation to prevent caching (`WHERE n1.class = '1' AND n1.txId > {threshold}`)
- Created comprehensive benchmark runner: `scripts/run_persistent_session_benchmarks.py`
- Supports filtering by database, dataset size, and specific queries
- Real-time progress output with `flush=True`
- Suppressed Sirius stdout to avoid output spam

### 3. Performance Analysis ✅

#### GPU Acceleration Sweet Spot
- **Best performance**: 2-hop queries on large datasets
- **Crossover point**: ~5M edges for GPU to outperform CPU
- **Initialization overhead**: GPU has fixed overhead (~7-8s) that dominates on small datasets

#### Recursive CTE Discovery 🎯
**Major finding**: DuckDB's CPU-based recursive CTE is **significantly faster** than GPU for complex graph traversal:
- Full 20-hop BFS on 5M dataset: **0.45s** (DuckDB recursive CTE)
- vs. Iterative GPU approach: ~77s for 10 iterations (7s overhead per iteration)
- **Recommendation**: Use DuckDB CPU for k-hop and shortest_path queries

### 4. Experimental: Iterative GPU BFS ✅
Created `scripts/iterative_gpu_bfs.py` implementing true breadth-first search:
- Runs each hop as separate GPU query (avoids 3-hop segfaults)
- Python handles iteration control and visited tracking
- Fully exhaustive until no new nodes found
- **Limitation**: Cannot maintain persistent Sirius session via stdin (DuckDB `-init` flag limitation)
- **Current performance**: ~7s per iteration (data reload overhead)
- **Conclusion**: CPU recursive CTE is superior for this use case

### 5. Documentation ✅
- Updated `README.md` with GPU compatibility matrix
- Cleaned up `adhoc_tests/` directory (removed 37+ obsolete test files)
- Added `adhoc_tests/README.md` explaining reference files
- Cleaned old result CSVs
- Created comprehensive query documentation

## 📊 Final Results Summary

### Verified GPU-Compatible Queries

✅ **Fully GPU-accelerated** (Production Ready):
1. **1_hop**: Single-hop neighbor traversal (2-table JOIN)
2. **2_hop**: Two-hop reachability analysis (4-table JOIN)

⚠️ **Partial GPU acceleration** (Not Recommended):
3. **k_hop**: Variable k-hop traversal → UNION ALL triggers partial fallback
4. **shortest_path**: Shortest path → UNION ALL triggers partial fallback
   - **Better alternative**: DuckDB recursive CTE (~0.45s vs multi-second GPU)

❌ **Not GPU-compatible**:
5. **3_hop**: Causes segmentation faults (6-table JOIN exceeds GPU limits)
6. **Queries with constant columns**: Trigger GPU fallback or hangs

### Performance Characteristics

**When to use GPU (Sirius)**:
- Simple 1-hop and 2-hop queries
- Large datasets (>5M edges)
- Queries without UNION ALL, recursion, or constant columns

**When to use CPU (DuckDB)**:
- k-hop traversal (use recursive CTE)
- Shortest path analysis (use recursive CTE)
- Small datasets (<5M edges)
- Queries with UNION ALL or complex aggregations

## 📁 Key Files

### Production Scripts
- `scripts/run_persistent_session_benchmarks.py` - Main benchmark runner
  - Supports `--db`, `--size`, `--query`, `--session-queries` parameters
  - Generates CSVs in `results/persistent_session/`
- `scripts/02_run_benchmarks.py` - Core benchmark functions
  - Comment stripping for inline `--` SQL comments
  - Quote escaping for `gpu_processing()` calls
  - Persistent session mode with query variation
- `scripts/iterative_gpu_bfs.py` - Experimental iterative BFS (not recommended)

### Query Definitions
- `sql/queries/1_hop.sql` - ✅ GPU-accelerated
- `sql/queries/2_hop.sql` - ✅ GPU-accelerated
- `sql/queries/3_hop.sql` - ❌ Causes segfaults (reference only)
- `sql/queries/k_hop.sql` - ⚠️ Use DuckDB recursive CTE instead
- `sql/queries/shortest_path.sql` - ⚠️ Use DuckDB recursive CTE instead

### Results
- `results/persistent_session/` - Latest benchmark results
- `results/aws_large_datasets/` - AWS benchmarks (50M, 100M datasets)
- `results/figures/` - Visualization outputs

### Test/Reference Files
- `adhoc_tests/` - Reference test scripts and SQL files (see `adhoc_tests/README.md`)
- `test_databases.py` - Modified during testing

## 🔍 Known Limitations

### GPU SQL Restrictions (Sirius)
- ❌ `UNION ALL` → partial CPU fallback (joins run on GPU, union on CPU)
- ❌ 3+ hop queries (6+ table JOINs) → segmentation faults
- ❌ Constant literal columns → GPU fallback or hangs
- ❌ Recursive CTEs → not supported (use CPU instead)
- ❌ `DISTINCT` in SELECT → forces fallback
- ✅ `JOIN`, `GROUP BY`, `ORDER BY` → work on GPU
- ✅ Aggregate functions (`MAX`, `COUNT`) → work on GPU

### DuckDB Session Limitations
- Cannot maintain persistent Sirius session via stdin (due to `-init` flag behavior)
- Each iteration requires data reload (~7-8s overhead)
- Makes iterative algorithms impractical on GPU

### Impact
- k-hop and shortest_path queries run better on CPU (recursive CTE)
- 3-hop queries excluded entirely from GPU benchmarks
- Constant columns must be removed for GPU execution

## 🚀 Recommendations

### For Production Use

1. **Use GPU (Sirius) for**:
   - 1-hop and 2-hop queries on large datasets (>5M edges)
   - Simple joins without UNION ALL
   - Queries without constant columns

2. **Use CPU (DuckDB) for**:
   - k-hop traversal (recursive CTE: ~0.45s for 20 hops on 5M)
   - Shortest path analysis (recursive CTE)
   - Small datasets (<5M edges)
   - Any query with UNION ALL or recursion

3. **Benchmark Configuration**:
   - Use persistent session mode with 100 queries per test
   - Vary queries to prevent caching
   - Exclude 3-hop from all benchmarks
   - Suppress Sirius stdout for clean output

### For Future Work

1. **Investigate Sirius GPU limitations**: Why do 6-table joins cause segfaults?
2. **Profile recursive CTE performance**: Understand why CPU outperforms GPU
3. **Test on larger datasets**: 50M, 100M edges (already prepared)
4. **Explore persistent session workarounds**: Can we keep Sirius process alive between queries?

## 📊 Dataset Status

All datasets in 2-column format (txId, class):
- `data/processed/nodes_100k.csv` + `edges_100k.csv` (1.6MB + 2.1MB)
- `data/processed/nodes_1m.csv` + `edges_1m.csv` (15.8MB + 18.7MB)
- `data/processed/nodes_5m.csv` + `edges_5m.csv` (69.5MB + 90.5MB)
- `data/processed/nodes_20m.csv` + `edges_20m.csv` (272.8MB + 347.1MB)
- `data/processed/nodes_50m.csv` + `edges_50m.csv` (AWS only)
- `data/processed/nodes_100m.csv` + `edges_100m.csv` (AWS only)

## ✨ Cleanup Complete

- Removed 37+ obsolete test files from `adhoc_tests/`
- Cleaned old CSV results from `results/`
- Updated all documentation
- Added READMEs where needed
- Removed `/tmp` test files
