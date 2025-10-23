#!/bin/bash
# Build Sirius with all required environment variables

set -e  # Exit on error

echo "========================================="
echo "Building Sirius"
echo "========================================="
echo ""

# Navigate to sirius directory
cd ~/crypto-transaction-analysis/sirius

# Activate conda environment
echo "Activating conda environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate crypto-analysis
echo "✓ Conda environment activated: $(conda info --envs | grep '*' | awk '{print $1}')"
echo ""

# Set required environment variables
echo "Setting environment variables..."
export LIBCUDF_ENV_PREFIX=$CONDA_PREFIX
export LDFLAGS="-Wl,-rpath,$CONDA_PREFIX/lib -L$CONDA_PREFIX/lib $LDFLAGS"
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

echo "✓ LIBCUDF_ENV_PREFIX = $LIBCUDF_ENV_PREFIX"
echo "✓ CONDA_PREFIX = $CONDA_PREFIX"
echo ""

# Run Sirius setup script
echo "Running Sirius setup script..."
source setup_sirius.sh
echo ""

# Clean previous build if it exists
if [ -d "build" ]; then
    echo "Cleaning previous build..."
    rm -rf build
    echo "✓ Build directory cleaned"
    echo ""
fi

# Build with all available cores
NPROC=$(nproc)
echo "Building Sirius with $NPROC cores..."
echo "This will take 10-30 minutes..."
echo ""

make -j $NPROC

echo ""
echo "========================================="
echo "Build Complete!"
echo "========================================="
echo ""

# Verify build
if [ -f "build/release/duckdb" ]; then
    echo "✓ Sirius binary created successfully"
    echo "  Location: $(pwd)/build/release/duckdb"
    echo ""
    echo "Testing binary:"
    ./build/release/duckdb --version
    echo ""
    echo "========================================="
    echo "Sirius is ready to use!"
    echo "========================================="
    echo ""
    echo "To use Sirius:"
    echo "  1. conda activate crypto-analysis"
    echo "  2. cd ~/crypto-transaction-analysis/sirius"
    echo "  3. ./build/release/duckdb"
    echo ""
    echo "In the Sirius CLI:"
    echo "  call gpu_buffer_init('1 GB', '2 GB');"
    echo "  call gpu_processing('SELECT ...');"
    echo ""
else
    echo "✗ Build failed - binary not found"
    exit 1
fi
