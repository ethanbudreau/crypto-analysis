#!/bin/bash
# Fix Sirius clone issue - clean up and re-clone

set -e  # Exit on error

echo "========================================="
echo "Fixing Sirius Clone"
echo "========================================="
echo ""

cd ~/crypto-transaction-analysis

# Remove existing sirius directory
if [ -d "sirius" ]; then
    echo "Removing existing sirius directory..."
    rm -rf sirius
    echo "✓ Old sirius directory removed"
else
    echo "✓ No existing sirius directory found"
fi
echo ""

# Fresh clone with submodules
echo "Cloning Sirius repository (this may take a few minutes)..."
git clone --recurse-submodules https://github.com/sirius-db/sirius.git
echo "✓ Sirius cloned successfully"
echo ""

echo "========================================="
echo "Sirius Clone Fixed!"
echo "========================================="
echo ""
echo "You can now continue with the build:"
echo "  cd ~/crypto-transaction-analysis/sirius"
echo "  source setup_sirius.sh"
echo "  make -j \$(nproc)"
echo ""
echo "Or run the full setup script again:"
echo "  bash ~/crypto-transaction-analysis/setup/install_sirius_after_cuda.sh"
echo ""
