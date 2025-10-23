#!/bin/bash
# Master pipeline script
# Runs the complete benchmark pipeline from data prep to visualization

set -e  # Exit on error

echo "========================================="
echo "CRYPTO TRANSACTION ANALYSIS PIPELINE"
echo "========================================="
echo ""

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]] && [[ -z "${CONDA_DEFAULT_ENV}" ]]; then
    echo "⚠ Warning: No virtual environment detected"
    echo ""
    echo "Please activate your environment first:"
    echo "  source venv/bin/activate"
    echo "  OR"
    echo "  conda activate crypto-analysis"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Data Preparation
echo ""
echo "Step 1/3: Preparing dataset..."
echo "========================================"
python scripts/01_prepare_data.py
if [ $? -ne 0 ]; then
    echo "✗ Data preparation failed"
    exit 1
fi

# Step 2: Run Benchmarks
echo ""
echo "Step 2/3: Running benchmarks..."
echo "========================================"
read -p "Run benchmarks on: (1) DuckDB only, (2) Sirius only, (3) Both? [1/2/3]: " choice

case $choice in
    1)
        python scripts/02_run_benchmarks.py --db duckdb --sizes 10k 50k 100k full
        ;;
    2)
        python scripts/02_run_benchmarks.py --db sirius --sizes 10k 50k 100k full
        ;;
    3)
        python scripts/02_run_benchmarks.py --db both --sizes 10k 50k 100k full
        ;;
    *)
        echo "Invalid choice. Running DuckDB only..."
        python scripts/02_run_benchmarks.py --db duckdb --sizes 10k 50k
        ;;
esac

if [ $? -ne 0 ]; then
    echo "✗ Benchmarks failed"
    exit 1
fi

# Step 3: Visualization
echo ""
echo "Step 3/3: Generating visualizations..."
echo "========================================"
python scripts/03_visualize.py
if [ $? -ne 0 ]; then
    echo "✗ Visualization failed"
    exit 1
fi

# Summary
echo ""
echo "========================================="
echo "PIPELINE COMPLETE!"
echo "========================================="
echo ""
echo "Results available in:"
echo "  - results/benchmarks.csv (raw data)"
echo "  - results/summary_table.csv (summary)"
echo "  - results/figures/ (visualizations)"
echo ""
echo "Next steps:"
echo "  - Review figures for insights"
echo "  - Analyze performance trends"
echo "  - Draft project report"
echo ""
