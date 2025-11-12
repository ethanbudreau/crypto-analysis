#!/bin/bash
# Quick start script for team members
# Automatically sets up the appropriate environment based on available hardware

set -e

echo "========================================="
echo "Crypto Transaction Analysis - Quick Start"
echo "========================================="
echo ""

# Check requirements first
echo "Checking system requirements..."
bash setup/check_requirements.sh
echo ""

# Determine setup mode
read -p "Do you have an NVIDIA GPU and want to setup Sirius? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Starting FULL setup (DuckDB + Sirius)..."
    echo ""

    # Check if GPU is available (required)
    if ! command -v nvidia-smi &> /dev/null; then
        echo "✗ Error: nvidia-smi not found. NVIDIA GPU required for Sirius."
        echo ""
        read -p "Continue with DuckDB-only setup instead? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            bash setup/setup_duckdb.sh
        else
            echo "Setup cancelled. Please install GPU drivers first."
            exit 1
        fi
    else
        # Full setup with Sirius
        bash setup/setup_sirius.sh
        echo ""
        echo "✓ Full setup complete (DuckDB + Sirius)"
    fi
else
    echo ""
    echo "🚀 Starting DuckDB-only setup..."
    echo ""
    bash setup/setup_duckdb.sh
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Quick reference:"
echo "  - Activate environment: source venv/bin/activate"
echo "                      OR: conda activate crypto-analysis (if using Sirius)"
echo "  - Prepare data: python scripts/01_prepare_data.py"
echo "  - Run benchmarks: python scripts/02_run_benchmarks.py"
echo "  - Visualize results: python scripts/03_visualize.py"
echo "  - Run everything: bash run_all.sh"
echo ""
echo "For detailed instructions, see SETUP.md"
echo ""
