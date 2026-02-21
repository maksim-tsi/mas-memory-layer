#!/bin/bash
#
# Script: run_goodai_remote_variant.sh
# Purpose: Run the GoodAI LTM benchmark against a MAS API Wall instance selected via AGENT_URL.
# Usage:
#   ./scripts/run_goodai_remote_variant.sh \
#     --agent-url "http://localhost:8081/v1/chat/completions" \
#     --agent-type full \
#     --agent-variant v1-min-skillwiring \
#     --config configurations/mas_remote_test.yml
#
# Notes:
# - This script does not start YAAM; it only runs the benchmark runner.
# - This script does not read `.env`. Provide required env vars externally.

set -e
set -u
set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BENCH_ROOT="$PROJECT_ROOT/benchmarks/goodai-ltm-benchmark"
BENCH_PYTHON="$BENCH_ROOT/.venv/bin/python"

AGENT_URL=""
AGENT_TYPE=""
AGENT_VARIANT=""
CONFIG_PATH=""
MAX_PROMPT_SIZE=""
RUN_NAME_BASE="goodai"
PROGRESS="tqdm"
TEST_FILTER=""
DATASET_PATH=""

function usage() {
    echo "Usage: $0 --agent-url URL --agent-type TYPE --agent-variant VARIANT --config PATH [options]"
    echo ""
    echo "Required:"
    echo "  --agent-url URL         Full OpenAI-compatible endpoint (e.g., http://host:8081/v1/chat/completions)"
    echo "  --agent-type TYPE       Agent type (e.g., full|rag|full_context)"
    echo "  --agent-variant VAR     Variant slug (e.g., baseline|v1-min-skillwiring)"
    echo "  --config PATH           Benchmark config path (relative to benchmarks/goodai-ltm-benchmark/)"
    echo ""
    echo "Options:"
    echo "  --max-prompt-size N     Pass -m/--max-prompt-size to runner (default: unset)"
    echo "  --run-name-base STR     Prefix for --run-name (default: goodai)"
    echo "  --progress MODE         tqdm|tk|none (default: tqdm)"
    echo "  --test-filter FILTER    Restrict to dataset/example (runner --test-filter)"
    echo "  --dataset-path PATH     Load examples from directory (runner --dataset-path)"
    echo "  -h, --help              Show this help"
    exit 1
}

function die() {
    echo -e "${RED}Error:${NC} $1"
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --agent-url)
            AGENT_URL="$2"
            shift 2
            ;;
        --agent-type)
            AGENT_TYPE="$2"
            shift 2
            ;;
        --agent-variant)
            AGENT_VARIANT="$2"
            shift 2
            ;;
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --max-prompt-size)
            MAX_PROMPT_SIZE="$2"
            shift 2
            ;;
        --run-name-base)
            RUN_NAME_BASE="$2"
            shift 2
            ;;
        --progress)
            PROGRESS="$2"
            shift 2
            ;;
        --test-filter)
            TEST_FILTER="$2"
            shift 2
            ;;
        --dataset-path)
            DATASET_PATH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

[ -n "$AGENT_URL" ] || die "--agent-url is required"
[ -n "$AGENT_TYPE" ] || die "--agent-type is required"
[ -n "$AGENT_VARIANT" ] || die "--agent-variant is required"
[ -n "$CONFIG_PATH" ] || die "--config is required"

[ -d "$BENCH_ROOT" ] || die "Benchmark directory not found: $BENCH_ROOT"
[ -x "$BENCH_PYTHON" ] || die "Benchmark venv not found at $BENCH_PYTHON (run: cd $BENCH_ROOT && poetry install)"

STAMP="$(date +%Y%m%d_%H%M%S)"
RUN_NAME="${RUN_NAME_BASE}__${AGENT_TYPE}__${AGENT_VARIANT}__${STAMP}"

echo -e "${BLUE}=== GoodAI LTM Benchmark (MAS remote) ===${NC}"
echo "AGENT_URL:      $AGENT_URL"
echo "agent_type:     $AGENT_TYPE"
echo "agent_variant:  $AGENT_VARIANT"
echo "run_name:       $RUN_NAME"
echo "config:         $CONFIG_PATH"
echo ""

cd "$BENCH_ROOT"

set -- \
    -m runner.run_benchmark \
    -c "$CONFIG_PATH" \
    -a mas-remote \
    --run-name "$RUN_NAME" \
    --progress "$PROGRESS" \
    -y

if [ -n "$MAX_PROMPT_SIZE" ]; then
    set -- "$@" -m "$MAX_PROMPT_SIZE"
fi
if [ -n "$TEST_FILTER" ]; then
    set -- "$@" --test-filter "$TEST_FILTER"
fi
if [ -n "$DATASET_PATH" ]; then
    set -- "$@" --dataset-path "$DATASET_PATH"
fi

AGENT_URL="$AGENT_URL" "$BENCH_PYTHON" "$@"

echo ""
echo -e "${GREEN}✅ Benchmark completed.${NC}"
echo -e "${YELLOW}Artifacts are stored under:${NC}"
echo "  $BENCH_ROOT/data/tests/$RUN_NAME/results/"
