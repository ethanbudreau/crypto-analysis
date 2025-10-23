#!/bin/bash
# Automated DuckDB setup for crypto-transaction-analysis project

set -e  # Exit on error

echo "========================================="
echo "DuckDB Setup"
echo "========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo "✓ pip upgraded"
echo ""

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Verify DuckDB installation
echo "Verifying DuckDB installation..."
python3 -c "import duckdb; print(f'DuckDB version: {duckdb.__version__}')"
echo "✓ DuckDB verified"
echo ""

echo "========================================="
echo "DuckDB Setup Complete!"
echo "========================================="
echo ""
echo "To activate the environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "Next steps:"
echo "  1. Download the Elliptic dataset: python scripts/01_prepare_data.py"
echo "  2. Run DuckDB benchmarks: python scripts/02_run_benchmarks.py --db duckdb"
echo ""
