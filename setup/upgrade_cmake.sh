#!/bin/bash
# Upgrade CMake to version 3.30 or newer for Sirius build

set -e  # Exit on error

echo "========================================="
echo "CMake Upgrade Script"
echo "========================================="
echo ""

# Check current version
echo "Current CMake version:"
cmake --version | head -n 1
echo ""

# Remove old CMake (installed via apt)
echo "Removing old CMake..."
sudo apt remove -y cmake
sudo apt autoremove -y
echo "✓ Old CMake removed"
echo ""

# Download and install latest CMake
echo "Installing CMake 3.30.5..."
cd /tmp

# Download CMake binary distribution
CMAKE_VERSION="3.30.5"
CMAKE_BUILD="0"
CMAKE_FULL_VERSION="${CMAKE_VERSION}"
echo "Downloading CMake ${CMAKE_FULL_VERSION}..."
wget -q https://github.com/Kitware/CMake/releases/download/v${CMAKE_FULL_VERSION}/cmake-${CMAKE_FULL_VERSION}-linux-x86_64.sh

# Install to /opt/cmake
echo "Installing to /opt/cmake..."
sudo mkdir -p /opt/cmake
sudo bash cmake-${CMAKE_FULL_VERSION}-linux-x86_64.sh --skip-license --prefix=/opt/cmake

# Create symbolic links
echo "Creating symbolic links..."
sudo ln -sf /opt/cmake/bin/cmake /usr/local/bin/cmake
sudo ln -sf /opt/cmake/bin/ctest /usr/local/bin/ctest
sudo ln -sf /opt/cmake/bin/cpack /usr/local/bin/cpack

# Clean up
rm cmake-${CMAKE_FULL_VERSION}-linux-x86_64.sh

echo "✓ CMake installed successfully"
echo ""

# Verify installation
echo "New CMake version:"
cmake --version | head -n 1
echo ""

# Check if version is sufficient
CMAKE_VERSION_OUTPUT=$(cmake --version | head -n 1 | grep -oP '\d+\.\d+\.\d+')
if [ "$(printf '%s\n' "3.30.0" "$CMAKE_VERSION_OUTPUT" | sort -V | head -n1)" = "3.30.0" ]; then
    echo "✓ CMake version is sufficient for Sirius build"
else
    echo "⚠ Warning: CMake version may still be too old"
fi
echo ""

echo "========================================="
echo "CMake Upgrade Complete!"
echo "========================================="
echo ""
echo "You can now continue with Sirius setup:"
echo "  bash ~/crypto-transaction-analysis/setup/install_sirius_after_cuda.sh"
echo ""
