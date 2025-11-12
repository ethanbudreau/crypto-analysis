#!/bin/bash
# Automated Sirius setup for crypto-transaction-analysis project
# REQUIREMENTS: Ubuntu >= 20.04, NVIDIA GPU, CUDA >= 11.2, CMake >= 3.30

set -e  # Exit on error

echo "========================================="
echo "Sirius GPU Database Setup"
echo "========================================="
echo ""

# Verify prerequisites
echo "Checking prerequisites..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "✗ Error: nvidia-smi not found. GPU required for Sirius."
    exit 1
fi

# if ! command -v nvcc &> /dev/null; then
#     echo "✗ Error: nvcc not found. CUDA >= 11.2 required."
#     exit 1
# fi

if ! command -v cmake &> /dev/null; then
    echo "✗ Error: cmake not found. Install with: sudo apt install cmake"
    exit 1
fi

if ! command -v conda &> /dev/null; then
    echo "✗ Error: conda not found. Install Miniconda from:"
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "✓ All prerequisites found"
echo ""

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y git g++ cmake ninja-build libssl-dev
echo "✓ System dependencies installed"
echo ""

# Create conda environment
echo "Creating conda environment for Sirius..."
if conda env list | grep -q "crypto-analysis"; then
    echo "✓ Environment 'crypto-analysis' already exists"
    read -p "Remove and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        conda env remove -n crypto-analysis
        conda env create -f environment.yml
    fi
else
    conda env create -f environment.yml
fi
echo "✓ Conda environment ready"
echo ""

# Activate conda environment
echo "Activating conda environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate crypto-analysis
echo "✓ Environment activated"
echo ""

# Set libcudf environment variable
echo "Setting libcudf environment variable..."
export LIBCUDF_ENV_PREFIX=$CONDA_PREFIX
echo "export LIBCUDF_ENV_PREFIX=$CONDA_PREFIX" >> ~/.bashrc
echo "✓ LIBCUDF_ENV_PREFIX set to $CONDA_PREFIX"
echo ""

# Clone Sirius repository
if [ ! -d "sirius" ]; then
    echo "Cloning Sirius repository..."
    git clone --recurse-submodules https://github.com/sirius-db/sirius.git
    echo "✓ Sirius cloned"
else
    echo "✓ Sirius directory already exists"
fi
echo ""

# Build Sirius
cd sirius
echo "Building Sirius (this may take 10-20 minutes with 16 vCPUs)..."
source setup_sirius.sh

# Set LDFLAGS for libcudf linking
export LDFLAGS="-Wl,-rpath,$CONDA_PREFIX/lib -L$CONDA_PREFIX/lib $LDFLAGS"

# Build with all available cores
NPROC=$(nproc)
echo "Building with $NPROC cores..."
make -j $NPROC

echo "✓ Sirius built successfully"
echo ""

# Optional: Install DuckDB Python package with Sirius support
echo "Installing DuckDB Python package with Sirius support..."
cd duckdb/tools/pythonpkg/
pip install .
cd ../../../..
echo "✓ DuckDB Python package installed"
echo ""

echo "========================================="
echo "Sirius Setup Complete!"
echo "========================================="
echo ""
echo "To use Sirius in the future:"
echo "  1. Activate conda: conda activate crypto-analysis"
echo "  2. Start Sirius CLI: ./sirius/build/release/duckdb mydb.duckdb"
echo "  3. Initialize GPU: call gpu_buffer_init('1 GB', '2 GB');"
echo "  4. Run GPU query: call gpu_processing('SELECT...');"
echo ""
echo "Note: Sirius binary located at: ./sirius/build/release/duckdb"
echo ""
