#!/bin/bash
set -e
set -u
set -o pipefail

# =================================================================================================
# MAS Memory Layer - Mixed 100-Question Sequential Benchmark Script
# =================================================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BENCH_ROOT="$PROJECT_ROOT/benchmarks/goodai-ltm-benchmark"
BENCH_PYTHON="$BENCH_ROOT/.venv/bin/python"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_NAME_BASE="MAS Mixed 100 Run"
CONFIG_FILE="configurations/mas_mixed_100.yml"

if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    . "$PROJECT_ROOT/.env"
    set +a
else
    echo "Error: .env file not found!"
    exit 1
fi

if [ ! -x "$BENCH_PYTHON" ]; then
    echo "Error: benchmark virtualenv not found at $BENCH_PYTHON"
    echo "Run: cd $BENCH_ROOT && poetry install"
    exit 1
fi

mkdir -p "$PROJECT_ROOT/logs"

echo "================================================================="
echo "Starting Pre-flight Checks..."
echo "================================================================="
echo "Launching wrappers..."
"$PROJECT_ROOT/scripts/start_benchmark_wrappers.sh" &
WRAPPER_PID=$!

echo "Waiting for wrappers to initialize..."
sleep 15

cd "$BENCH_ROOT"

get_log_file() {
    echo "$PROJECT_ROOT/logs/run_mas_100_${1}_${TIMESTAMP}.log"
}

run_agent() {
    agent="$1"
    run_name="${RUN_NAME_BASE} - ${agent} - ${TIMESTAMP}"
    log_file=$(get_log_file "$agent")

    echo "Starting ${agent}..."
    echo "  > Run name: ${run_name}"
    echo "  > Log: ${log_file}"

    "$BENCH_PYTHON" -m runner.run_benchmark \
        -c "$CONFIG_FILE" \
        -a "$agent" \
        --run-name "$run_name" \
        -y \
        > "$log_file" 2>&1

    echo "Finished ${agent}."
    sleep 5
}

echo "================================================================="
echo "Starting Sequential Benchmarks..."
echo "================================================================="

run_agent "mas-full"
run_agent "mas-rag"
run_agent "mas-full-context"
run_agent "gemini"

echo "================================================================="
echo "All Benchmarks Completed."
echo "Check logs in logs/ directory."
echo "================================================================="

echo "Cleaning up wrappers..."
kill "$WRAPPER_PID" >/dev/null 2>&1 || true
pkill -f "agent_wrapper.py" >/dev/null 2>&1 || true
