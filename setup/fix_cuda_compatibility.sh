#!/bin/bash
# Fix CUDA/GCC compatibility issue for Sirius build

set -e  # Exit on error

echo "========================================="
echo "Fixing CUDA/GCC Compatibility"
echo "========================================="
echo ""

# Check current GCC version
echo "Current GCC version:"
gcc --version | head -n 1
echo ""

# The issue: CUDA 12.0 from apt doesn't support GCC 13.3 well
# Solution: Install GCC 12 and use it for CUDA compilation

echo "Installing GCC 12 for CUDA compatibility..."
sudo apt update
sudo apt install -y gcc-12 g++-12
echo "✓ GCC 12 installed"
echo ""

# Set up alternatives so we can switch GCC versions
echo "Setting up GCC alternatives..."
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120 \
    --slave /usr/bin/g++ g++ /usr/bin/g++-12 \
    --slave /usr/bin/gcov gcov /usr/bin/gcov-12

sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 130 \
    --slave /usr/bin/g++ g++ /usr/bin/g++-13 \
    --slave /usr/bin/gcov gcov /usr/bin/gcov-13

# Select GCC 12 for CUDA compatibility
echo "Switching to GCC 12..."
sudo update-alternatives --set gcc /usr/bin/gcc-12
echo "✓ GCC 12 set as default"
echo ""

# Verify
echo "Verifying GCC version:"
gcc --version | head -n 1
echo ""

# Clean up any previous build attempts
echo "Cleaning previous build attempts..."
cd ~/crypto-transaction-analysis/sirius
if [ -d "build" ]; then
    rm -rf build
    echo "✓ Build directory cleaned"
fi
echo ""

echo "========================================="
echo "CUDA/GCC Compatibility Fixed!"
echo "========================================="
echo ""
echo "GCC 12 is now the default compiler."
echo ""
echo "Next steps:"
echo "1. Activate conda environment:"
echo "   conda activate crypto-analysis"
echo ""
echo "2. Build Sirius:"
echo "   cd ~/crypto-transaction-analysis/sirius"
echo "   source setup_sirius.sh"
echo "   export LDFLAGS=\"-Wl,-rpath,\$CONDA_PREFIX/lib -L\$CONDA_PREFIX/lib \$LDFLAGS\""
echo "   make -j \$(nproc)"
echo ""
echo "Note: After Sirius is built, you can switch back to GCC 13 if needed:"
echo "   sudo update-alternatives --set gcc /usr/bin/gcc-13"
echo ""
