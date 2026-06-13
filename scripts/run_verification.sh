#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BENCH_ROOT="${GOODAI_BENCHMARK_DIR:-$PROJECT_ROOT/../goodai-ltm-benchmark-yaam}"
BENCH_PYTHON="$BENCH_ROOT/.venv/bin/python"

# Start wrappers in background
echo "Starting wrappers..."
./scripts/start_benchmark_wrappers.sh > logs/verification_wrappers.log 2>&1 &
WRAPPER_PID=$!

# Wait for wrappers to be healthy
echo "Waiting for wrappers (pid $WRAPPER_PID) to initialize..."
# Simple wait loop checking logs or just failing if run_benchmark fails
# better: wait for port 8080 to be open
for i in {1..30}; do
    if curl -s http://localhost:8080/health | grep "ok" > /dev/null; then
        echo "Wrappers are ready."
        break
    fi
    sleep 2
    echo "Waiting..."
done

# Run Benchmark
echo "Running verification benchmark..."
if [ ! -x "$BENCH_PYTHON" ]; then
    echo "Benchmark venv not found at $BENCH_PYTHON"
    echo "Set GOODAI_BENCHMARK_DIR to the external benchmark checkout and run poetry install there."
    exit 1
fi
cd "$BENCH_ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
"$BENCH_PYTHON" runner/run_benchmark.py --configuration configurations/mas_verification_run.yml --agent-name mas-full

# Cleanup
echo "Stopping wrappers..."
kill $WRAPPER_PID
