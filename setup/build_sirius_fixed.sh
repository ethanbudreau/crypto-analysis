#!/bin/bash
# Build Sirius - handles existing substrait directory issue

set -e  # Exit on error

echo "========================================="
echo "Building Sirius (Fixed)"
echo "========================================="
echo ""

# Navigate to sirius directory
cd ~/crypto-transaction-analysis/sirius

# Activate conda environment
echo "Activating conda environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate crypto-analysis
echo "✓ Conda environment activated"
echo ""

# Set required environment variables
echo "Setting environment variables..."
export LIBCUDF_ENV_PREFIX=$CONDA_PREFIX
export LDFLAGS="-Wl,-rpath,$CONDA_PREFIX/lib -L$CONDA_PREFIX/lib $LDFLAGS"
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export SIRIUS_HOME_PATH=$(pwd)

echo "✓ LIBCUDF_ENV_PREFIX = $LIBCUDF_ENV_PREFIX"
echo "✓ SIRIUS_HOME_PATH = $SIRIUS_HOME_PATH"
echo ""

# Instead of running setup_sirius.sh, do the steps manually with fixes
echo "Initializing git submodules..."
git submodule update --init --recursive
echo "✓ Submodules initialized"
echo ""

# Handle substrait clone (which might already exist)
echo "Setting up substrait extension..."
cd duckdb
mkdir -p extension_external
cd extension_external

if [ -d "substrait" ]; then
    echo "✓ substrait directory already exists"
    cd substrait
    # Make sure we're on the right commit
    git fetch origin 2>/dev/null || true
    git reset --hard ec9f8725df7aa22bae7217ece2f221ac37563da4
else
    echo "Cloning substrait..."
    git clone https://github.com/duckdb/substrait.git
    cd substrait
    git reset --hard ec9f8725df7aa22bae7217ece2f221ac37563da4
fi
echo "✓ substrait ready"
echo ""

# Return to Sirius home
cd $SIRIUS_HOME_PATH

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
echo "Build started at: $(date)"
echo ""

make -j $NPROC

echo ""
echo "Build completed at: $(date)"
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

    # Install Python package
    echo "Installing DuckDB Python package with Sirius support..."
    cd duckdb/tools/pythonpkg/
    pip install -e .
    cd $SIRIUS_HOME_PATH
    echo "✓ DuckDB Python package installed"
    echo ""

    echo "========================================="
    echo "Sirius is ready to use!"
    echo "========================================="
    echo ""
    echo "To use Sirius CLI:"
    echo "  conda activate crypto-analysis"
    echo "  cd ~/crypto-transaction-analysis/sirius"
    echo "  ./build/release/duckdb"
    echo ""
    echo "In the Sirius CLI, initialize GPU:"
    echo "  call gpu_buffer_init('1 GB', '2 GB');"
    echo "  call gpu_processing('SELECT ...');"
    echo ""
    echo "To use in Python:"
    echo "  conda activate crypto-analysis"
    echo "  python"
    echo "  >>> import duckdb"
    echo "  >>> # Use DuckDB with GPU support"
    echo ""
else
    echo "✗ Build failed - binary not found"
    exit 1
fi
