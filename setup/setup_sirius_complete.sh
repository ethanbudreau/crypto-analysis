#!/bin/bash
# Complete Sirius GPU Database Setup
# Automated setup script that handles all known issues
# REQUIREMENTS: Ubuntu >= 20.04, NVIDIA GPU, sudo access

set -e  # Exit on error

echo "========================================="
echo "Sirius GPU Database - Complete Setup"
echo "========================================="
echo ""
echo "This script will:"
echo "  1. Check system requirements"
echo "  2. Install/upgrade CMake to 3.30+"
echo "  3. Configure GCC compatibility for CUDA"
echo "  4. Install Miniconda (if needed)"
echo "  5. Create conda environment with libcudf"
echo "  6. Clone and build Sirius from source"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi
echo ""

# ==========================================
# Step 1: Check Prerequisites
# ==========================================
echo "Step 1/6: Checking prerequisites..."

if ! command -v nvidia-smi &> /dev/null; then
    echo "✗ Error: nvidia-smi not found. NVIDIA GPU required for Sirius."
    exit 1
fi
echo "✓ NVIDIA GPU detected:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

if ! command -v git &> /dev/null; then
    echo "Installing git..."
    sudo apt-get update && sudo apt-get install -y git
fi
echo "✓ Git available"
echo ""

# ==========================================
# Step 2: Upgrade CMake to 3.30+
# ==========================================
echo "Step 2/6: Checking CMake version..."

CMAKE_REQUIRED="3.30.0"
if command -v cmake &> /dev/null; then
    CMAKE_VERSION=$(cmake --version | head -n 1 | grep -oP '\d+\.\d+\.\d+')
    echo "Current CMake version: $CMAKE_VERSION"

    if [ "$(printf '%s\n' "$CMAKE_REQUIRED" "$CMAKE_VERSION" | sort -V | head -n1)" != "$CMAKE_REQUIRED" ]; then
        echo "CMake version too old, upgrading to 3.30.5..."
        sudo apt remove -y cmake 2>/dev/null || true

        cd /tmp
        CMAKE_VERSION="3.30.5"
        wget -q https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-x86_64.sh
        sudo mkdir -p /opt/cmake
        sudo bash cmake-${CMAKE_VERSION}-linux-x86_64.sh --skip-license --prefix=/opt/cmake
        sudo ln -sf /opt/cmake/bin/cmake /usr/local/bin/cmake
        sudo ln -sf /opt/cmake/bin/ctest /usr/local/bin/ctest
        sudo ln -sf /opt/cmake/bin/cpack /usr/local/bin/cpack
        rm cmake-${CMAKE_VERSION}-linux-x86_64.sh
        echo "✓ CMake upgraded to $(cmake --version | head -n 1)"
    else
        echo "✓ CMake version is sufficient"
    fi
else
    echo "CMake not found, installing 3.30.5..."
    cd /tmp
    CMAKE_VERSION="3.30.5"
    wget -q https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-x86_64.sh
    sudo mkdir -p /opt/cmake
    sudo bash cmake-${CMAKE_VERSION}-linux-x86_64.sh --skip-license --prefix=/opt/cmake
    sudo ln -sf /opt/cmake/bin/cmake /usr/local/bin/cmake
    sudo ln -sf /opt/cmake/bin/ctest /usr/local/bin/ctest
    sudo ln -sf /opt/cmake/bin/cpack /usr/local/bin/cpack
    rm cmake-${CMAKE_VERSION}-linux-x86_64.sh
    echo "✓ CMake installed: $(cmake --version | head -n 1)"
fi
echo ""

# ==========================================
# Step 3: Fix GCC Compatibility
# ==========================================
echo "Step 3/6: Checking CUDA Toolkit..."

if ! command -v nvcc &> /dev/null; then
    echo "Installing CUDA Toolkit..."
    sudo apt-get update
    sudo apt-get install -y nvidia-cuda-toolkit

    # Add CUDA to PATH
    if ! grep -q "cuda/bin" ~/.bashrc; then
        echo "" >> ~/.bashrc
        echo "# CUDA Toolkit paths" >> ~/.bashrc
        echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
        echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
    fi
    echo "✓ CUDA Toolkit installed"
else
    CUDA_VERSION=$(nvcc --version | grep release | awk '{print $6}' | cut -d',' -f1)
    echo "✓ CUDA Toolkit already installed: $CUDA_VERSION"
fi

# Ensure CUDA paths are set for current session
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export CUDA_HOME=/usr/local/cuda

# Install GCC 12 for CUDA compatibility
GCC_VERSION=$(gcc --version | head -n 1 | grep -oP '\d+\.\d+' | head -n 1)
echo "Current GCC version: $GCC_VERSION"

if ! command -v gcc-12 &> /dev/null; then
    echo "Installing GCC 12 for CUDA compatibility..."
    sudo apt-get update
    sudo apt-get install -y gcc-12 g++-12
    echo "✓ GCC 12 installed"
fi

# Set up GCC alternatives
echo "Configuring GCC alternatives..."
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120 \
    --slave /usr/bin/g++ g++ /usr/bin/g++-12 \
    --slave /usr/bin/gcov gcov /usr/bin/gcov-12 2>/dev/null || true

if command -v gcc-13 &> /dev/null; then
    sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 130 \
        --slave /usr/bin/g++ g++ /usr/bin/g++-13 \
        --slave /usr/bin/gcov gcov /usr/bin/gcov-13 2>/dev/null || true
fi

# Switch to GCC 12 for CUDA compatibility
sudo update-alternatives --set gcc /usr/bin/gcc-12
echo "✓ GCC switched to version 12 for CUDA compatibility"
echo ""

# ==========================================
# Step 4: Install Miniconda
# ==========================================
echo "Step 4/6: Checking Miniconda..."

if [ -d "$HOME/miniconda3" ]; then
    echo "✓ Miniconda directory exists at $HOME/miniconda3"
    # Make sure conda is initialized
    if ! command -v conda &> /dev/null; then
        echo "Initializing conda for current shell..."
        $HOME/miniconda3/bin/conda init bash
        source ~/.bashrc
    fi
    echo "✓ Miniconda version: $($HOME/miniconda3/bin/conda --version)"
elif ! command -v conda &> /dev/null; then
    echo "Installing Miniconda..."
    cd ~
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p $HOME/miniconda3
    $HOME/miniconda3/bin/conda init bash
    rm miniconda.sh

    # Source bashrc to get conda in current session
    source ~/.bashrc
    echo "✓ Miniconda installed"
else
    echo "✓ Miniconda already available: $(conda --version)"
fi

# Accept conda Terms of Service
echo "Accepting conda Terms of Service..."
$HOME/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main 2>/dev/null || true
$HOME/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r 2>/dev/null || true
echo "✓ Conda TOS accepted"
echo ""

# ==========================================
# Step 5: Create Conda Environment
# ==========================================
echo "Step 5/6: Creating conda environment..."

# Make sure we're in the project directory
cd ~/crypto-transaction-analysis

# Source conda directly from known location
source $HOME/miniconda3/etc/profile.d/conda.sh

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

conda activate crypto-analysis
echo "✓ Conda environment activated"

# Set LIBCUDF environment variable
export LIBCUDF_ENV_PREFIX=$CONDA_PREFIX
if ! grep -q "LIBCUDF_ENV_PREFIX" ~/.bashrc; then
    echo 'export LIBCUDF_ENV_PREFIX=$CONDA_PREFIX' >> ~/.bashrc
fi
echo "✓ LIBCUDF_ENV_PREFIX configured"
echo ""

# ==========================================
# Step 6: Clone and Build Sirius
# ==========================================
echo "Step 6/6: Building Sirius..."

# Install system dependencies
echo "Installing build dependencies..."
sudo apt-get update
sudo apt-get install -y git g++ cmake ninja-build libssl-dev

# Clone Sirius if not already present
if [ ! -d "sirius" ]; then
    echo "Cloning Sirius repository..."
    git clone --recurse-submodules https://github.com/sirius-db/sirius.git
    echo "✓ Sirius cloned"
else
    echo "✓ Sirius directory already exists"
fi

cd sirius

# Set all required environment variables
export SIRIUS_HOME_PATH=$(pwd)
export LDFLAGS="-Wl,-rpath,$CONDA_PREFIX/lib -L$CONDA_PREFIX/lib $LDFLAGS"
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export CUDA_HOME=/usr/local/cuda

# Initialize submodules
echo "Initializing git submodules..."
git submodule update --init --recursive

# Set up substrait extension (handle if already exists)
echo "Setting up substrait extension..."
cd duckdb
mkdir -p extension_external
cd extension_external

if [ -d "substrait" ]; then
    echo "✓ substrait directory already exists"
    cd substrait
    git fetch origin 2>/dev/null || true
    git reset --hard ec9f8725df7aa22bae7217ece2f221ac37563da4
else
    git clone https://github.com/duckdb/substrait.git
    cd substrait
    git reset --hard ec9f8725df7aa22bae7217ece2f221ac37563da4
fi

cd $SIRIUS_HOME_PATH

# Clean previous build
if [ -d "build" ]; then
    echo "Cleaning previous build..."
    rm -rf build
fi

# Build Sirius
NPROC=$(nproc)
echo "Building Sirius with $NPROC cores (this takes 10-30 minutes)..."
echo "Started at: $(date)"
make -j $NPROC

# Verify build
if [ ! -f "build/release/duckdb" ]; then
    echo "✗ Build failed - binary not found"
    exit 1
fi

echo "✓ Sirius built successfully!"
echo "Completed at: $(date)"

# Install Python package
echo "Installing DuckDB Python package with Sirius support..."
cd duckdb/tools/pythonpkg/
pip install -e .
cd $SIRIUS_HOME_PATH

echo ""
echo "========================================="
echo "Sirius Setup Complete! 🚀"
echo "========================================="
echo ""
echo "Binary location: $(pwd)/build/release/duckdb"
./build/release/duckdb --version
echo ""
echo "To use Sirius:"
echo "  1. conda activate crypto-analysis"
echo "  2. cd ~/crypto-transaction-analysis/sirius"
echo "  3. ./build/release/duckdb"
echo ""
echo "In the Sirius CLI:"
echo "  call gpu_buffer_init('512 MB', '1 GB');"
echo "  call gpu_processing('SELECT ...');"
echo ""
echo "Test the installation:"
echo "  cd ~/crypto-transaction-analysis"
echo "  python test_databases.py"
echo ""
