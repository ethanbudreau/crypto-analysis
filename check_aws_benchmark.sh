#!/bin/bash
# Check AWS benchmark status
# Usage: bash check_aws_benchmark.sh

echo "======================================================================"
echo "AWS BENCHMARK STATUS CHECK"
echo "======================================================================"
echo ""

# Check if benchmark process is running
echo "📊 BENCHMARK PROCESS:"
ssh ubuntu@184.72.137.4 "ps aux | grep 'run_persistent_session' | grep -v grep" || echo "  ⚠️  No benchmark process running"
echo ""

# Get detailed process info if running
# Get the actual Python process with high CPU usage, not the conda wrapper
BENCHMARK_PID=$(ssh ubuntu@184.72.137.4 "ps aux | grep 'run_persistent_session' | grep -v grep | grep -v 'conda run' | awk '{print \$2}' | head -1")

if [ ! -z "$BENCHMARK_PID" ]; then
    echo "🕐 PROCESS DETAILS (PID $BENCHMARK_PID):"
    PROCESS_INFO=$(ssh ubuntu@184.72.137.4 "ps -p $BENCHMARK_PID -o pid,state,%cpu,%mem,etime,cmd --no-headers")
    echo "$PROCESS_INFO"

    # Extract CPU usage for interpretation
    CPU_PCT=$(echo "$PROCESS_INFO" | awk '{print $3}' | cut -d. -f1)
    ELAPSED=$(echo "$PROCESS_INFO" | awk '{print $5}')
    echo ""

    # Check for child processes
    echo "🔧 ACTIVE SUBPROCESS:"
    ssh ubuntu@184.72.137.4 "pstree -p $BENCHMARK_PID 2>/dev/null | grep duckdb" || echo "  No duckdb subprocess (between tests or in Python code)"
    echo ""

    # Get GPU status
    echo "⚡ RESOURCE UTILIZATION:"
    GPU_INFO=$(ssh ubuntu@184.72.137.4 "nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used --format=csv,noheader,nounits")
    GPU_COMPUTE=$(echo "$GPU_INFO" | awk -F, '{print $1}' | xargs)
    GPU_MEM=$(echo "$GPU_INFO" | awk -F, '{print $2}' | xargs)
    VRAM_MB=$(echo "$GPU_INFO" | awk -F, '{print $3}' | xargs)

    printf "  %-20s %6s%%  (using ~%d cores)\n" "CPU Usage:" "$CPU_PCT" $((CPU_PCT / 100))
    printf "  %-20s %6s%%\n" "GPU Compute:" "$GPU_COMPUTE"
    printf "  %-20s %6s%%  (%s MB allocated)\n" "GPU Memory:" "$GPU_MEM" "$VRAM_MB"
    echo ""

    # Interpret what's happening
    echo "📍 CURRENT PHASE:"
    if [ "$GPU_COMPUTE" -lt 5 ]; then
        echo "  ➜ Running DuckDB (CPU) tests"
        echo "  ➜ Estimated progress: 50-80% complete (DuckDB is slower phase)"
        echo "  ➜ Next: Sirius GPU tests (much faster, ~10-20 min remaining after switch)"
    else
        echo "  ➜ Running Sirius (GPU) tests"
        echo "  ➜ GPU active - final phase, should complete soon!"
    fi
    echo ""
fi

# Check for result files
echo "📁 RESULT FILES:"
ssh ubuntu@184.72.137.4 "ls -lth results/persistent_session/*.csv 2>/dev/null | head -3" || echo "  No results yet (written at benchmark completion)"
echo ""

# Show interpretation guide
echo "======================================================================"
echo "QUICK REFERENCE GUIDE:"
echo "======================================================================"
echo ""
echo "BENCHMARK PHASES:"
echo "  Phase 1: DuckDB tests (16 tests, slower)"
echo "    → CPU: 400-600%  GPU: 0%"
echo "    → Estimated: 60-90 minutes"
echo ""
echo "  Phase 2: Sirius GPU tests (16 tests, faster)"
echo "    → CPU: 50-200%  GPU: 30-90%"
echo "    → Estimated: 10-30 minutes"
echo ""
echo "PROCESS STATES:"
echo "  'R' = Actively running query"
echo "  'S' = Sleeping/waiting for subprocess"
echo ""
echo "TOTAL EXPECTED TIME: 80-120 minutes (32 tests)"
echo "  (Local: 17 min, AWS CPU is ~5x slower)"
echo ""
