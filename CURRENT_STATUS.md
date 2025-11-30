# Current Status - GPU Benchmark Project

**Last Updated**: 2025-11-29 (AWS benchmarks completed 2025-11-30)

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

#### AWS Benchmarks Completed (2025-11-30)
- **Platform**: AWS g4dn.2xlarge (8 vCPU Xeon + Tesla T4)
- **Method**: Query variation to prevent caching
- **Coverage**: All 4 dataset sizes (100k, 1m, 5m, 20m) × 4 queries
- **Key finding**: GPU shows up to 3.1x speedup on 2-hop queries (20M dataset)

#### Performance Characteristics by Platform

**AWS Tesla T4** (Best GPU results):
- 2-hop query on 20M dataset: **3.1x GPU speedup** (5871ms → 1895ms)
- 2-hop query on 5M dataset: **2.5x GPU speedup** (686ms → 273ms)
- 1-hop queries: Mixed results (slight CPU advantage on smaller datasets)
- k-hop/shortest_path: CPU faster due to UNION ALL fallback

**Local RTX 3050** (Strong CPU dominance):
- Intel Core Ultra 7 265k CPU outperforms RTX 3050 GPU on all queries
- Example (5M dataset): 2-hop is 2.4x faster on CPU (182ms vs 430ms)
- CPU advantage: Higher core count (20 cores) and clock speed (3.9-5.5 GHz)

#### Caching Discovery and Resolution 🎯
**Major finding**: Query caching significantly distorts benchmark results:
- Identical queries showed 71x performance improvement (likely cached)
- **Solution**: Vary WHERE clause per query (`WHERE n1.txId > {threshold}`)
- All benchmarks now use query variation for realistic timing
- Prevents both DuckDB result cache and Sirius query plan cache

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
- 2-hop queries on large datasets (>5M edges) with slower CPUs (AWS)
- Production environments with limited CPU resources
- Queries without UNION ALL, recursion, or constant columns
- **Best case**: 3.1x speedup on AWS Tesla T4 for 2-hop/20M dataset

**When to use CPU (DuckDB)**:
- k-hop traversal (use recursive CTE - much faster)
- Shortest path analysis (use recursive CTE)
- Any platform with fast multi-core CPU (20+ cores)
- Local development (Intel Core Ultra 7 outperforms RTX 3050)
- Queries with UNION ALL or complex aggregations
- Small-medium datasets (<5M edges)

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
- `results/persistent_session/` - Local benchmark results (varied queries)
- `results/aws_persistent_session/` - AWS benchmark results (100k-20m datasets, varied queries)
- `results/figures/` - Visualization outputs comparing local vs AWS performance

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
   - 2-hop queries on large datasets (>10M edges) in CPU-constrained environments
   - AWS or cloud platforms with limited CPU cores (8 or fewer)
   - Workloads where 2-3x speedup justifies GPU complexity
   - **Not recommended** on local systems with high-end CPUs (20+ cores)

2. **Use CPU (DuckDB) for**:
   - k-hop traversal (recursive CTE: ~0.45s for 20 hops on 5M) ⭐ **Recommended**
   - Shortest path analysis (recursive CTE) ⭐ **Recommended**
   - 1-hop queries (CPU competitive on all platforms)
   - Any platform with modern multi-core CPU (Intel Core Ultra, Ryzen 9, etc.)
   - Small-medium datasets (<10M edges)
   - Any query with UNION ALL or recursion

3. **Benchmark Configuration**:
   - Use persistent session mode with 50-100 queries per test
   - **CRITICAL**: Vary queries to prevent caching (`WHERE txId > {threshold}`)
   - Exclude 3-hop from all benchmarks (causes segfaults)
   - Suppress Sirius stdout for clean output
   - Test on target hardware - CPU architecture matters significantly

### For Future Work

1. **Investigate Sirius GPU limitations**: Why do 6-table joins cause segfaults?
2. **Profile recursive CTE performance**: Understand why CPU outperforms GPU for graph traversal
3. **Test on larger datasets**: 50M, 100M edges on AWS (datasets prepared, benchmarks pending)
4. **Explore persistent session workarounds**: Can we keep Sirius process alive between queries?
5. **Test on different GPU architectures**: Compare RTX 3050 vs Tesla T4 vs A100
6. **Investigate local GPU performance**: Why does RTX 3050 underperform relative to CPU?

## 📊 Dataset Status

All datasets in 2-column format (txId, class):

**Local + AWS:**
- `data/processed/nodes_100k.csv` + `edges_100k.csv` (1.6MB + 2.1MB) ✅ Benchmarked
- `data/processed/nodes_1m.csv` + `edges_1m.csv` (15.8MB + 18.7MB) ✅ Benchmarked
- `data/processed/nodes_5m.csv` + `edges_5m.csv` (69.5MB + 90.5MB) ✅ Benchmarked
- `data/processed/nodes_20m.csv` + `edges_20m.csv` (272.8MB + 347.1MB) ✅ Benchmarked

**AWS only (prepared, benchmarks pending):**
- `data/processed/nodes_50m.csv` + `edges_50m.csv`
- `data/processed/nodes_100m.csv` + `edges_100m.csv`

## ✨ Recent Updates (2025-11-29/30)

### Caching Investigation and Fix
- Discovered query caching causing 71x performance anomalies
- Implemented query variation using `WHERE txId > {threshold}` predicates
- Re-ran all benchmarks with varied queries for accurate results

### AWS Benchmarks Completed
- Completed full benchmark suite on AWS g4dn.2xlarge (Tesla T4)
- Downloaded results to `results/aws_persistent_session/`
- Updated visualizations comparing local vs AWS performance
- Key finding: GPU shows best performance on AWS (3.1x for 2-hop/20M)

### Documentation Updates
- Updated README.md with actual performance results (not inflated cached results)
- Updated CURRENT_STATUS.md with AWS completion status
- Generated comparison visualizations in `results/figures/`

### Cleanup Previously Completed
- Removed 37+ obsolete test files from `adhoc_tests/`
- Cleaned old CSV results from `results/`
- Added READMEs where needed
