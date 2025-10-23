#!/bin/bash
# Sirius setup script - Run AFTER CUDA toolkit is installed
# This script configures CUDA paths, installs Miniconda, and sets up Sirius

set -e  # Exit on error

echo "========================================="
echo "Sirius Setup - Part 2"
echo "========================================="
echo ""

# Step 1: Configure CUDA paths in bashrc
echo "Step 1: Configuring CUDA paths..."
if ! grep -q "cuda/bin" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# CUDA Toolkit paths" >> ~/.bashrc
    echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
    echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
    echo "✓ CUDA paths added to ~/.bashrc"
else
    echo "✓ CUDA paths already in ~/.bashrc"
fi

# Apply changes to current session
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
echo ""

# Verify CUDA installation
echo "Verifying CUDA installation..."
if command -v nvcc &> /dev/null; then
    echo "✓ CUDA compiler found:"
    nvcc --version | head -n 1
else
    echo "✗ Error: nvcc not found. Make sure CUDA toolkit installation completed successfully."
    echo "You may need to:"
    echo "  1. Restart your terminal"
    echo "  2. Run: source ~/.bashrc"
    echo "  3. Check that CUDA is installed: ls /usr/local/cuda/bin/nvcc"
    exit 1
fi
echo ""

# Step 2: Install Miniconda
echo "Step 2: Installing Miniconda..."
if command -v conda &> /dev/null; then
    echo "✓ Conda already installed:"
    conda --version
else
    echo "Downloading Miniconda..."
    cd ~
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh

    echo "Installing Miniconda (this will take a few minutes)..."
    bash miniconda.sh -b -p $HOME/miniconda3

    echo "Initializing conda..."
    $HOME/miniconda3/bin/conda init bash

    # Clean up installer
    rm miniconda.sh

    echo "✓ Miniconda installed successfully"
    echo ""
    echo "IMPORTANT: You need to restart your terminal or run:"
    echo "  source ~/.bashrc"
    echo ""
    echo "Then run this script again to continue with Sirius setup."
    exit 0
fi
echo ""

# Step 3: Navigate to project directory
cd ~/crypto-transaction-analysis

# Step 4: Install system dependencies for Sirius
echo "Step 3: Installing system dependencies..."
echo "This requires sudo access..."
sudo apt-get update
sudo apt-get install -y git g++ cmake ninja-build libssl-dev
echo "✓ System dependencies installed"
echo ""

# Step 5: Create conda environment
echo "Step 4: Creating conda environment..."
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

# Step 6: Activate conda environment
echo "Step 5: Activating conda environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate crypto-analysis
echo "✓ Environment activated"
echo ""

# Step 7: Set libcudf environment variable
echo "Step 6: Setting libcudf environment variable..."
export LIBCUDF_ENV_PREFIX=$CONDA_PREFIX
if ! grep -q "LIBCUDF_ENV_PREFIX" ~/.bashrc; then
    echo "export LIBCUDF_ENV_PREFIX=\$CONDA_PREFIX" >> ~/.bashrc
fi
echo "✓ LIBCUDF_ENV_PREFIX set to $CONDA_PREFIX"
echo ""

# Step 8: Clone Sirius repository
echo "Step 7: Cloning Sirius repository..."
if [ ! -d "sirius" ]; then
    git clone --recurse-submodules https://github.com/sirius-db/sirius.git
    echo "✓ Sirius cloned"
else
    echo "✓ Sirius directory already exists"
fi
echo ""

# Step 9: Build Sirius
echo "Step 8: Building Sirius..."
cd sirius
echo "This may take 10-30 minutes depending on your CPU..."
echo ""

# Run Sirius setup script
source setup_sirius.sh

# Set LDFLAGS for libcudf linking
export LDFLAGS="-Wl,-rpath,$CONDA_PREFIX/lib -L$CONDA_PREFIX/lib $LDFLAGS"

# Build with all available cores
NPROC=$(nproc)
echo "Building with $NPROC cores..."
make -j $NPROC

echo "✓ Sirius built successfully"
echo ""

# Step 10: Verify build
echo "Step 9: Verifying Sirius build..."
if [ -f "build/release/duckdb" ]; then
    echo "✓ Sirius binary found at: $(pwd)/build/release/duckdb"
    ./build/release/duckdb --version
else
    echo "✗ Error: Sirius binary not found"
    exit 1
fi
echo ""

# Step 11: Optional - Install DuckDB Python package
echo "Step 10: Installing DuckDB Python package with Sirius support..."
cd duckdb/tools/pythonpkg/
pip install .
cd ../../..
echo "✓ DuckDB Python package installed"
echo ""

# Return to project root
cd ~/crypto-transaction-analysis

echo "========================================="
echo "Sirius Setup Complete! 🚀"
echo "========================================="
echo ""
echo "To use Sirius:"
echo "  1. Activate conda: conda activate crypto-analysis"
echo "  2. Start Sirius CLI: ./sirius/build/release/duckdb"
echo "  3. In the CLI, initialize GPU:"
echo "     call gpu_buffer_init('1 GB', '2 GB');"
echo "  4. Run GPU queries:"
echo "     call gpu_processing('SELECT ...');"
echo ""
echo "Next steps:"
echo "  - Download the Elliptic dataset"
echo "  - Run: python scripts/01_prepare_data.py"
echo "  - Run benchmarks: python scripts/02_run_benchmarks.py"
echo ""
