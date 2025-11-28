#!/bin/bash
# Automated Sirius setup for crypto-transaction-analysis project (AWS-optimized)
# REQUIREMENTS: Ubuntu >= 20.04, NVIDIA GPU, CUDA >= 11.2, CMake >= 3.30
# ASSUMES: AWS image with most dependencies pre-installed

set -e  # Exit on error

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "Sirius GPU Database Setup (AWS)"
echo "========================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Verify prerequisites
echo "Checking prerequisites..."

if ! command -v nvidia-smi &> /dev/null; then
    echo "✗ Error: nvidia-smi not found. GPU required for Sirius."
    exit 1
else
    echo "✓ nvidia-smi found"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
fi

if ! command -v cmake &> /dev/null; then
    echo "✗ Error: cmake not found. Install with: sudo apt install cmake"
    exit 1
else
    CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
    echo "✓ cmake found (version $CMAKE_VERSION)"
fi

if ! command -v conda &> /dev/null; then
    echo "✗ Error: conda not found. Install Miniconda from:"
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
else
    echo "✓ conda found"
fi

echo "✓ All prerequisites found"
echo ""

# Verify conda environment is activated (required on AWS images)
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "✗ Error: No conda environment activated. AWS images should have an environment pre-activated."
    echo "  Please activate your conda environment first."
    exit 1
fi

echo "✓ Using active conda environment: $CONDA_DEFAULT_ENV"
echo "  CONDA_PREFIX: $CONDA_PREFIX"
if [ -n "$LIBCUDF_ENV_PREFIX" ]; then
    echo "  LIBCUDF_ENV_PREFIX: $LIBCUDF_ENV_PREFIX"
fi
echo ""

# Initialize conda if needed (for conda commands)
if [ -f "$(conda info --base)/etc/profile.d/conda.sh" ]; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
fi

# Install/update packages from environment.yml into current environment
if [ -f "environment.yml" ]; then
    echo "Installing packages from environment.yml into $CONDA_DEFAULT_ENV..."
    
    # Create a temporary environment.yml with the current env name
    TEMP_ENV_YML=$(mktemp)
    sed "s/^name:.*/name: $CONDA_DEFAULT_ENV/" environment.yml > "$TEMP_ENV_YML"
    
    # Update environment with packages from environment.yml
    conda env update -n "$CONDA_DEFAULT_ENV" -f "$TEMP_ENV_YML" --prune || {
        echo "⚠ Note: Some conda packages may conflict or already be installed"
        echo "  This is normal if packages are already present"
    }
    
    # Clean up temp file
    rm -f "$TEMP_ENV_YML"
    
    echo "✓ Packages updated in existing environment"
else
    echo "⚠ environment.yml not found, skipping package installation"
fi
echo ""

# Install system dependencies (only if missing, AWS images may have them)
echo "Checking system dependencies..."
MISSING_PACKAGES=()

for pkg in git g++ ninja-build libssl-dev; do
    if ! dpkg -l | grep -q "^ii  $pkg "; then
        MISSING_PACKAGES+=("$pkg")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo "Installing missing packages: ${MISSING_PACKAGES[*]}..."
    sudo apt-get update
    sudo apt-get install -y "${MISSING_PACKAGES[@]}"
    echo "✓ Missing packages installed"
else
    echo "✓ All system packages already installed"
fi
echo ""

# Using existing conda environment (always true on AWS)
echo "✓ Using existing conda environment: $CONDA_DEFAULT_ENV"
echo ""

# Set libcudf environment variable
echo "Setting libcudf environment variable..."
export LIBCUDF_ENV_PREFIX=$CONDA_PREFIX
echo "✓ LIBCUDF_ENV_PREFIX set to $CONDA_PREFIX"

# Ensure CUDA paths are set (common on AWS GPU instances)
if [ -d "/usr/local/cuda" ]; then
    # Check if already in PATH/LD_LIBRARY_PATH
    if [[ ":$PATH:" != *":/usr/local/cuda/bin:"* ]]; then
        export PATH=/usr/local/cuda/bin:$PATH
    fi
    if [[ ":$LD_LIBRARY_PATH:" != *":/usr/local/cuda/lib64:"* ]]; then
        export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
    fi
    echo "✓ CUDA paths detected and set"
fi

# Add to bashrc if not already present
if ! grep -q "LIBCUDF_ENV_PREFIX" ~/.bashrc 2>/dev/null; then
    echo "export LIBCUDF_ENV_PREFIX=\$CONDA_PREFIX" >> ~/.bashrc
fi

if [ -d "/usr/local/cuda" ] && ! grep -q "/usr/local/cuda/bin" ~/.bashrc 2>/dev/null; then
    echo "export PATH=/usr/local/cuda/bin:\$PATH" >> ~/.bashrc
    echo "export LD_LIBRARY_PATH=/usr/local/cuda/lib64:\$LD_LIBRARY_PATH" >> ~/.bashrc
fi

echo ""

# Clone Sirius repository
if [ ! -d "sirius" ]; then
    echo "Cloning Sirius repository..."
    git clone --recurse-submodules https://github.com/sirius-db/sirius.git
    echo "✓ Sirius cloned"
else
    echo "✓ Sirius directory already exists"
    # Update submodules in case they're outdated
    cd sirius
    git submodule update --init --recursive
    cd ..
fi
echo ""

# Check if Sirius is already built
SIRIUS_BINARY="$PROJECT_ROOT/sirius/build/release/duckdb"
if [ -f "$SIRIUS_BINARY" ] && [ "${REBUILD_SIRIUS:-no}" != "yes" ]; then
    echo "✓ Sirius binary already exists at $SIRIUS_BINARY"
    echo "  Set REBUILD_SIRIUS=yes to force rebuild"
else
    # Build Sirius
    cd sirius
    echo "Building Sirius (this may take 10-20 minutes with 16 vCPUs)..."
    
    # Run setup script if it exists and hasn't been run
    if [ -f "setup_sirius.sh" ]; then
        source setup_sirius.sh
    fi
    
    # Set LDFLAGS for libcudf linking
    export LDFLAGS="-Wl,-rpath,$CONDA_PREFIX/lib -L$CONDA_PREFIX/lib $LDFLAGS"
    
    # Build with all available cores
    NPROC=$(nproc)
    echo "Building with $NPROC cores..."
    make -j $NPROC
    
    echo "✓ Sirius built successfully"
    cd ..
fi
echo ""

# Optional: Install DuckDB Python package with Sirius support
if [ -d "sirius/duckdb/tools/pythonpkg" ]; then
    echo "Installing DuckDB Python package with Sirius support..."
    cd sirius/duckdb/tools/pythonpkg/
    pip install . --quiet
    cd "$PROJECT_ROOT"
    echo "✓ DuckDB Python package installed"
else
    echo "⚠ DuckDB Python package directory not found, skipping..."
fi
echo ""

# Verify installation
echo "Verifying installation..."
if [ -f "$SIRIUS_BINARY" ]; then
    echo "✓ Sirius binary found: $SIRIUS_BINARY"
    ls -lh "$SIRIUS_BINARY"
else
    echo "✗ Warning: Sirius binary not found at expected location"
fi

echo ""
echo "========================================="
echo "Sirius Setup Complete!"
echo "========================================="
echo ""
echo "Current environment: $CONDA_DEFAULT_ENV"
echo "CONDA_PREFIX: $CONDA_PREFIX"
echo "LIBCUDF_ENV_PREFIX: ${LIBCUDF_ENV_PREFIX:-not set}"
echo ""
echo "To use Sirius in the future:"
echo "  1. Ensure conda environment is activated: $CONDA_DEFAULT_ENV"
echo "     (Already active if you just ran this script)"
echo "  2. Navigate to project: cd $PROJECT_ROOT"
echo "  3. Start Sirius CLI: ./sirius/build/release/duckdb mydb.duckdb"
echo "  4. Initialize GPU: call gpu_buffer_init('1 GB', '2 GB');"
echo "  5. Run GPU query: call gpu_processing('SELECT...');"
echo ""
echo "Note: Sirius binary located at: $SIRIUS_BINARY"
echo ""
echo "Environment variables:"
echo "  - REBUILD_SIRIUS=yes  : Force rebuild Sirius from scratch"
echo ""
