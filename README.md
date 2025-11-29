# Cryptocurrency Transaction Analysis with GPU-Accelerated Databases

Performance comparison of CPU-based (DuckDB) vs GPU-accelerated (Sirius) graph databases for detecting illicit Bitcoin transactions.

## Team Members
- **Omkar Khade** - okhade@wisc.edu
- **Handan Hu** - handan.hu@wisc.edu
- **Ethan Budreau** - ebudreau@wisc.edu
- **Ashvin Sehgal** - asehgal9@wisc.edu

## Project Overview

This project evaluates whether GPU-accelerated databases can significantly improve the efficiency of analyzing cryptocurrency transaction networks for illicit activity detection. We compare:

- **DuckDB** (CPU-based SQL analytics engine)
- **Sirius** (GPU-accelerated database with DuckDB integration)

Using the **Elliptic Bitcoin Transaction Dataset** (203K+ nodes, 234K+ edges), we benchmark graph traversal queries including:
- 1-hop and 2-hop reachability from known illicit nodes
- k-hop traversal (3-4 hops)
- Shortest path analysis

### 🎯 Key Findings

**GPU acceleration provides up to 10.6x speedup** on large datasets for complex graph traversal queries:

#### Performance by Dataset Size

**20M Edge Dataset** (⭐ Peak GPU Performance)
| Query | DuckDB (CPU) | Sirius (GPU) | GPU Speedup |
|-------|--------------|--------------|-------------|
| 1_hop | 69.31 ms | 47.51 ms | 1.46x faster |
| 2_hop | 461.34 ms | **49.80 ms** | **9.26x faster** ⭐ |
| 3_hop | 476.59 ms | **45.06 ms** | **10.58x faster** ⭐ |

**5M Edge Dataset** (GPU Crossover Point)
| Query | DuckDB (CPU) | Sirius (GPU) | GPU Speedup |
|-------|--------------|--------------|-------------|
| 1_hop | 21.17 ms | 44.60 ms | 0.47x (CPU wins) |
| 2_hop | 108.60 ms | **38.48 ms** | **2.82x faster** |
| 3_hop | 104.84 ms | **40.33 ms** | **2.60x faster** |

**1M Edge Dataset** (Mixed Results)
| Query | DuckDB (CPU) | Sirius (GPU) | Result |
|-------|--------------|--------------|--------|
| 1_hop | 9.89 ms | 15.37 ms | CPU 1.55x faster |
| 2_hop | 22.44 ms | **13.01 ms** | GPU 1.72x faster |
| 3_hop | 27.07 ms | **17.11 ms** | GPU 1.58x faster |

**100k Edge Dataset** (CPU Wins on Simple Queries)
| Query | DuckDB (CPU) | Sirius (GPU) | Result |
|-------|--------------|--------------|--------|
| 1_hop | **5.27 ms** | 9.90 ms | CPU 1.88x faster |
| 2_hop | 10.24 ms | **7.02 ms** | GPU 1.46x faster |
| 3_hop | 12.23 ms | **7.21 ms** | GPU 1.70x faster |

#### Key Insights

1. **GPU wins at scale**: 10x speedup on 20M datasets for multi-hop traversal
2. **Crossover point**: GPU becomes advantageous around 5M edges for complex queries
3. **Query complexity matters**: 2-hop and 3-hop queries benefit more from GPU than 1-hop
4. **Initialization overhead**: GPU has overhead that impacts small datasets

#### GPU Compatibility

✅ **GPU-accelerated queries**: `1_hop_gpu`, `2_hop_gpu`, `3_hop_gpu`

❌ **CPU fallback** (UNION ALL not GPU-compatible):
- `k_hop_gpu` - Variable k-hop traversal
- `shortest_path_gpu` - Shortest path analysis

**Overall Performance:**
- **Sirius average**: 28.0 ms per query (24 tests)
- **DuckDB average**: 110.7 ms per query (24 tests)
- **Overall GPU advantage**: 3.95x speedup

> 📊 **Methodology**: All benchmarks use persistent session mode (100 queries per session) to amortize initialization overhead and measure true query execution performance. See [VERIFIED_GPU_BENCHMARK_RESULTS.md](VERIFIED_GPU_BENCHMARK_RESULTS.md) for detailed analysis.

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd crypto-transaction-analysis

# 2. Run automated setup
bash setup/quick_start.sh

# 3. Activate environment
source venv/bin/activate  # For DuckDB-only
# OR
conda activate crypto-analysis  # For full setup with Sirius

# 4. Run benchmarks
python scripts/run_persistent_session_benchmarks.py
```

See [SETUP.md](SETUP.md) for detailed installation instructions.

## Project Structure

```
crypto-transaction-analysis/
├── setup/                  # Automated setup scripts
│   ├── quick_start.sh      # One-command setup
│   ├── check_requirements.sh
│   ├── setup_duckdb.sh
│   └── setup_sirius_complete.sh
│
├── data/
│   ├── raw/                # Original Elliptic dataset
│   └── processed/          # Processed datasets (100K, 1M, 5M, 20M edges)
│
├── sql/                    # SQL query definitions
│   ├── duckdb/             # CPU-based queries
│   └── sirius/             # GPU-accelerated queries
│
├── scripts/                # Python automation scripts
│   ├── 01_prepare_data.py                    # Dataset preprocessing
│   ├── 02_run_benchmarks.py                  # Core benchmark functions
│   ├── 03_visualize.py                       # Results visualization
│   ├── run_persistent_session_benchmarks.py  # Main benchmark runner
│   └── create_slim_datasets.py               # Dataset optimization
│
├── adhoc_tests/            # Ad-hoc SQL test files
├── notebooks/              # Jupyter notebooks for exploration
└── results/                # Benchmark outputs and CSV data
```

## System Requirements

### Minimum (DuckDB Only)
- Python 3.9+
- 8+ GB RAM
- 5+ GB storage

### Full Setup (DuckDB + Sirius)
- Ubuntu 20.04+
- NVIDIA GPU (Volta or newer)
- CUDA 11.2+
- 16+ vCPUs (for compilation)
- 16+ GB RAM, 4+ GB VRAM

## Usage

### Individual Steps

```bash
# 1. Download dataset manually
# Visit https://www.kaggle.com/datasets/ellipticco/elliptic-data-set
# Download the ZIP and move to: data/raw/elliptic-data-set.zip

# 2. Prepare dataset (extract & preprocess)
python scripts/01_prepare_data.py

# 3. Run benchmarks
# Full benchmark suite (recommended)
python scripts/run_persistent_session_benchmarks.py --db both

# Quick test (10 queries per session)
python scripts/run_persistent_session_benchmarks.py --quick

# Specific database only
python scripts/run_persistent_session_benchmarks.py --db sirius

# 4. Generate visualizations
python scripts/03_visualize.py
```

### Full Benchmark Suite

```bash
# Run all benchmarks with persistent sessions (100 queries each)
python scripts/run_persistent_session_benchmarks.py

# Or run specific database only
python scripts/run_persistent_session_benchmarks.py --db duckdb
python scripts/run_persistent_session_benchmarks.py --db sirius

# Quick test mode (10 queries per session)
python scripts/run_persistent_session_benchmarks.py --quick
```

### Interactive Exploration

```bash
jupyter notebook
# Open notebooks/explore_data.ipynb
```

## Query Types

All queries are defined in SQL files under `sql/queries/` directory:

### GPU-Accelerated Queries (All Benchmarked)

1. **1-hop Reachability** (`sql/queries/1_hop.sql`)
   - Find transactions directly connected to known illicit nodes

2. **2-hop Reachability** (`sql/queries/2_hop.sql`)
   - Find transactions 2 steps away from illicit activity

3. **3-hop Reachability** (`sql/queries/3_hop.sql`)
   - Find transactions 3 steps away from illicit activity

4. **k-hop Traversal** (`sql/queries/k_hop.sql`)
   - Multi-step relationship exploration (1-4 hops)
   - ⚠️ Uses UNION ALL - causes partial CPU fallback in Sirius (JOINs on GPU, UNION on CPU)

5. **Shortest Path** (`sql/queries/shortest_path.sql`)
   - Compute distance to nearest illicit node (up to 5 hops)
   - ⚠️ Uses UNION ALL - causes partial CPU fallback in Sirius (JOINs on GPU, UNION on CPU)
   - **Coverage:** Graph analysis on 100k dataset shows this query captures 98.2% of all reachable nodes (2,642 of 2,690). Only 2.7% of nodes are reachable from illicit transactions (97.3% are in disconnected components). Maximum graph distance is 21 hops.

## Benchmarking

The benchmark suite measures:
- **Query execution time** (persistent session with 100 queries per test)
- **Memory/VRAM usage**
- **CPU/GPU utilization**

Results are scaled across dataset sizes:
- 100K edges
- 1M edges
- 5M edges
- 20M edges

## Technology Stack

- **Languages**: Python 3.10+, SQL
- **Databases**: DuckDB 1.4+, Sirius (GPU-native)
- **Data Processing**: pandas, numpy, pyarrow
- **Graph Analysis**: networkx
- **Visualization**: matplotlib, seaborn, plotly
- **Benchmarking**: psutil, py3nvml
- **Development**: Jupyter, pytest, black

## Timeline

- **Oct 24** - Environment setup, dataset preparation
- **Oct 31** - DuckDB query implementation
- **Nov 7** - Sirius query implementation
- **Nov 14** - Benchmarking and metrics collection
- **Nov 28** - Results analysis and visualization
- **Dec 1** - Presentation preparation
- **Dec 15** - Final report submission

## Dataset

**Elliptic Bitcoin Transaction Dataset**
- 203,769 transaction nodes
- 234,355 edges (Bitcoin flows)
- 2% labeled illicit, 21% labeled licit
- Anonymized, classification-oriented
- Source: [Elliptic Dataset](https://www.kaggle.com/ellipticco/elliptic-data-set)

## Key Contributions

1. **Comprehensive performance comparison** of CPU vs GPU graph databases for blockchain analytics
2. **Empirical characterization** of when GPU acceleration provides meaningful benefits
3. **Reusable benchmark framework** for future GPU-accelerated graph research

## References

See [project-proposal.txt](project-proposal.txt) for full academic references including:
- GPU-accelerated graph processing research
- Blockchain transaction analysis methodologies
- Anti-money laundering techniques
- DuckDB and Sirius technical papers

## Documentation

- **[README.md](README.md)** - This file: project overview and key findings
- **[VERIFIED_GPU_BENCHMARK_RESULTS.md](VERIFIED_GPU_BENCHMARK_RESULTS.md)** - Detailed performance analysis
- **[CURRENT_STATUS.md](CURRENT_STATUS.md)** - Project status and reproducibility guide
- **[SETUP.md](SETUP.md)** - Installation instructions
- **[project-proposal.txt](project-proposal.txt)** - Research proposal and references

## Troubleshooting

See [SETUP.md - Troubleshooting](SETUP.md#troubleshooting) section for common issues and solutions.

## License

This project is for academic research purposes as part of a database systems course.

## Acknowledgments

- Elliptic for providing the Bitcoin transaction dataset
- DuckDB team for the open-source analytics engine
- Sirius team for GPU-accelerated database technology
- Course instructors and teaching assistants
