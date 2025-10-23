#!/bin/bash
# Check system requirements for crypto-transaction-analysis project

echo "========================================="
echo "System Requirements Check"
echo "========================================="
echo ""

# Check OS
echo "1. Operating System:"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "   ✓ Linux detected"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "   Distribution: $NAME $VERSION"
    fi
else
    echo "   ⚠ Warning: Not Linux. Sirius requires Ubuntu >= 20.04"
fi
echo ""

# Check Python
echo "2. Python:"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "   ✓ Python $PYTHON_VERSION found"
    MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 9 ]; then
        echo "   ✓ Version is compatible (>= 3.9)"
    else
        echo "   ✗ Python 3.9+ required"
    fi
else
    echo "   ✗ Python3 not found"
fi
echo ""

# Check pip
echo "3. pip:"
if command -v pip3 &> /dev/null; then
    echo "   ✓ pip3 found"
else
    echo "   ✗ pip3 not found. Install with: sudo apt install python3-pip"
fi
echo ""

# Check for GPU (optional for DuckDB, required for Sirius)
echo "4. GPU Support (required for Sirius):"
if command -v nvidia-smi &> /dev/null; then
    echo "   ✓ NVIDIA driver detected"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | while read line; do
        echo "   GPU: $line"
    done
else
    echo "   ✗ nvidia-smi not found"
    echo "   Note: GPU is optional for DuckDB, but required for Sirius"
fi
echo ""

# Check CUDA (required for Sirius)
echo "5. CUDA (required for Sirius):"
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep release | awk '{print $5}' | cut -d',' -f1)
    echo "   ✓ CUDA $CUDA_VERSION found"
else
    echo "   ✗ nvcc not found"
    echo "   Note: CUDA >= 11.2 required for Sirius"
fi
echo ""

# Check CMake (required for Sirius)
echo "6. CMake (required for Sirius):"
if command -v cmake &> /dev/null; then
    CMAKE_VERSION=$(cmake --version | head -n1 | awk '{print $3}')
    echo "   ✓ CMake $CMAKE_VERSION found"
else
    echo "   ✗ CMake not found. Install with: sudo apt install cmake"
fi
echo ""

# Check conda (recommended for Sirius)
echo "7. Conda (recommended for Sirius):"
if command -v conda &> /dev/null; then
    CONDA_VERSION=$(conda --version | awk '{print $2}')
    echo "   ✓ Conda $CONDA_VERSION found"
else
    echo "   ⚠ Conda not found (recommended for Sirius libcudf setup)"
    echo "   Install from: https://docs.conda.io/en/latest/miniconda.html"
fi
echo ""

# Check git
echo "8. Git:"
if command -v git &> /dev/null; then
    echo "   ✓ Git found"
else
    echo "   ✗ Git not found. Install with: sudo apt install git"
fi
echo ""

echo "========================================="
echo "Summary:"
echo "========================================="
echo "✓ = Ready"
echo "⚠ = Optional/Warning"
echo "✗ = Missing (required)"
echo ""
echo "For DuckDB-only setup: Python 3.9+ and pip are sufficient"
echo "For Sirius setup: All requirements above are needed"
echo ""
