# Setup Instructions - Crypto Transaction Analysis

This guide will help you set up the development environment for analyzing Bitcoin transactions using DuckDB (CPU) and Sirius (GPU).

## Table of Contents
- [Quick Start (Recommended)](#quick-start-recommended)
- [System Requirements](#system-requirements)
- [Setup Options](#setup-options)
  - [Option 1: DuckDB Only (CPU-based)](#option-1-duckdb-only-cpu-based)
  - [Option 2: Full Setup (DuckDB + Sirius)](#option-2-full-setup-duckdb--sirius)
- [Manual Setup](#manual-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Quick Start (Recommended)

**For team members cloning this repository:**

```bash
# 1. Clone the repository
git clone <repository-url>
cd crypto-transaction-analysis

# 2. Run the quick start script
bash setup/quick_start.sh
```

This script will:
- Check your system requirements
- Detect available hardware (GPU/CUDA)
- Automatically choose the appropriate setup
- Install all dependencies
- Configure the environment

**That's it!** Skip to [Verification](#verification) to confirm everything works.

---

## System Requirements

### For DuckDB Only (Minimum)
- **OS**: Linux, macOS, or Windows
- **Python**: 3.9 or newer
- **pip**: Python package manager
- **RAM**: 8+ GB recommended
- **Storage**: 5+ GB for datasets

### For Sirius (Full Setup)
- **OS**: Ubuntu 20.04 or newer (Linux required)
- **GPU**: NVIDIA Volta or newer (Compute Capability 7.0+)
  - Examples: RTX 2000+, Tesla V100, A100, etc.
- **CUDA**: Version 11.2 or newer
- **CMake**: Version 3.30.4 or newer
- **CPUs**: 16+ vCPUs (for faster compilation)
- **VRAM**: 4+ GB GPU memory
- **RAM**: 16+ GB system memory
- **Storage**: 20+ GB (for Sirius build + datasets)

### Check Your System

Run the requirements checker:

```bash
bash setup/check_requirements.sh
```

This will show you which components are installed and which are missing.

---

## Setup Options

### Option 1: DuckDB Only (CPU-based)

**Best for:**
- Laptops/desktops without NVIDIA GPUs
- Initial development and testing
- Baseline performance benchmarking

**Setup:**

```bash
bash setup/setup_duckdb.sh
```

**What this does:**
1. Creates a Python virtual environment
2. Installs DuckDB and all Python dependencies
3. Sets up Jupyter notebooks

**Activate environment:**
```bash
source venv/bin/activate
```

---

### Option 2: Full Setup (DuckDB + Sirius)

**Best for:**
- Systems with NVIDIA GPUs
- Full benchmarking comparison
- GPU-accelerated query testing

**Prerequisites:**
- NVIDIA GPU with drivers installed
- sudo access (for installing CUDA, CMake, etc.)

**Setup:**

```bash
bash setup/setup_sirius_complete.sh
```

**What this does:**
1. Checks system requirements and GPU availability
2. Installs/upgrades CMake to 3.30.5
3. Installs CUDA Toolkit and configures GCC compatibility
4. Installs Miniconda (if needed)
5. Creates conda environment with libcudf
6. Clones and builds Sirius from source
7. Installs DuckDB Python package with GPU support

**This takes 15-30 minutes** depending on your CPU cores.

**Note:** The script handles all dependency installation and common setup issues automatically. For manual troubleshooting steps, see archived scripts in `setup/archive/`.

**Activate environment:**
```bash
conda activate crypto-analysis
```

---

## Manual Setup

### Installing CUDA (if not installed)

1. Download CUDA Toolkit from NVIDIA:
   ```
   https://developer.nvidia.com/cuda-downloads
   ```

2. For Ubuntu, use the .deb installer:
   ```bash
   wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
   sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
   wget https://developer.download.nvidia.com/compute/cuda/12.3.0/local_installers/cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb
   sudo dpkg -i cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb
   sudo cp /var/cuda-repo-ubuntu2204-12-3-local/cuda-*-keyring.gpg /usr/share/keyrings/
   sudo apt-get update
   sudo apt-get -y install cuda
   ```

3. Add to PATH (add to ~/.bashrc):
   ```bash
   export PATH=/usr/local/cuda/bin:$PATH
   export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
   ```

4. Verify:
   ```bash
   nvcc --version
   nvidia-smi
   ```

### Installing Miniconda (if not installed)

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
conda --version
```

### Manual Sirius Build

If the automated script fails:

```bash
# 1. Install dependencies
sudo apt-get update
sudo apt-get install -y git g++ cmake ninja-build libssl-dev

# 2. Create conda environment
conda env create -f environment.yml
conda activate crypto-analysis

# 3. Set environment variable
export LIBCUDF_ENV_PREFIX=$CONDA_PREFIX

# 4. Clone Sirius
git clone --recurse-submodules https://github.com/sirius-db/sirius.git
cd sirius

# 5. Build
source setup_sirius.sh
export LDFLAGS="-Wl,-rpath,$CONDA_PREFIX/lib -L$CONDA_PREFIX/lib $LDFLAGS"
make -j $(nproc)

# 6. Verify build
./build/release/duckdb --version
```

---

## Verification

### Verify DuckDB Installation

```bash
# Activate environment
source venv/bin/activate  # OR: conda activate crypto-analysis

# Test DuckDB
python3 -c "import duckdb; print(f'DuckDB version: {duckdb.__version__}')"

# Expected output: DuckDB version: 1.4.0 (or newer)
```

### Verify Sirius Installation

```bash
# Activate conda environment
conda activate crypto-analysis

# Check Sirius binary exists
ls -lh sirius/build/release/duckdb

# Start Sirius CLI
./sirius/build/release/duckdb test.duckdb

# In the Sirius prompt, test GPU:
# > call gpu_buffer_init('1 GB', '2 GB');
# > .quit
```

### Run Test Query

Create a test script `test_setup.py`:

```python
import duckdb

# Create in-memory database
conn = duckdb.connect(':memory:')

# Create test table
conn.execute("""
    CREATE TABLE transactions AS
    SELECT * FROM (VALUES
        (1, 'Alice', 100),
        (2, 'Bob', 200),
        (3, 'Charlie', 150)
    ) AS t(id, name, amount)
""")

# Query
result = conn.execute("SELECT * FROM transactions WHERE amount > 100").fetchall()
print(f"Query result: {result}")

conn.close()
print("✓ DuckDB test passed!")
```

Run it:
```bash
python test_setup.py
```

---

## Troubleshooting

### DuckDB Issues

**Problem:** `ImportError: No module named 'duckdb'`
```bash
# Solution: Ensure virtual environment is activated
source venv/bin/activate
pip install duckdb
```

**Problem:** Permission errors
```bash
# Solution: Don't use sudo with pip
pip install --user duckdb
```

### Sirius Issues

**Problem:** CUDA not found during build
```bash
# Solution: Add CUDA to PATH
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

**Problem:** libcudf linking errors
```bash
# Solution: Set LDFLAGS before building
export LDFLAGS="-Wl,-rpath,$CONDA_PREFIX/lib -L$CONDA_PREFIX/lib $LDFLAGS"
rm -rf sirius/build
cd sirius && make -j $(nproc)
```

**Problem:** Out of memory during compilation
```bash
# Solution: Use fewer cores
cd sirius
make -j 4  # Use only 4 cores instead of all
```

**Problem:** GPU buffer initialization fails
```bash
# Check GPU memory available
nvidia-smi

# Use smaller buffer sizes
call gpu_buffer_init('512 MB', '1 GB');
```

### AWS/Cloud Setup

If using AWS EC2:
- Use Sirius-provided AMI images (us-east-1, us-east-2, us-west-2)
- Recommended instances: g4dn.xlarge, g5.xlarge, p3.2xlarge
- All dependencies pre-installed on AMI

---

## Next Steps

Once setup is complete:

1. **Download Dataset:**
   ```bash
   python scripts/01_prepare_data.py
   ```

2. **Run Benchmarks:**
   ```bash
   python scripts/02_run_benchmarks.py
   ```

3. **Visualize Results:**
   ```bash
   python scripts/03_visualize.py
   ```

Or run everything at once:
```bash
bash run_all.sh
```

---

## Additional Resources

- **DuckDB Documentation**: https://duckdb.org/docs/
- **Sirius GitHub**: https://github.com/sirius-db/sirius
- **Elliptic Dataset**: https://www.kaggle.com/ellipticco/elliptic-data-set
- **CUDA Installation**: https://developer.nvidia.com/cuda-downloads
- **Project Proposal**: See `project-proposal.txt` for research background

---

## Getting Help

If you encounter issues not covered here:

1. Check system requirements with `bash setup/check_requirements.sh`
2. Review error messages carefully
3. Check GitHub Issues for similar problems
4. Contact team members

For project-specific questions, contact:
- Omkar Khade: okhade@wisc.edu
- Handan Hu: handan.hu@wisc.edu
- Ethan Budreau: ebudreau@wisc.edu
- Ashvin Sehgal: asehgal9@wisc.edu
