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
RUN_NAME=""
PROGRESS="tqdm"
TEST_FILTER=""
DATASET_PATH=""
PROVIDER=""
MODEL=""
PROMOTION_MODE=""
SKIP_PROVIDER_CHECK="false"

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
    echo "  --run-name STR          Explicit run name (overrides convention)"
    echo "  --provider NAME         Provider id for run-name convention (groq|gemini|mistral)"
    echo "  --model NAME            Model id for run-name convention (e.g., openai/gpt-oss-120b)"
    echo "  --promotion-mode MODE   Promotion mode for run-name convention (disabled|async|barrier)"
    echo "  --skip-provider-check   Skip /health + single-turn metadata gate"
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
        --run-name)
            RUN_NAME="$2"
            shift 2
            ;;
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --promotion-mode)
            PROMOTION_MODE="$2"
            shift 2
            ;;
        --skip-provider-check)
            SKIP_PROVIDER_CHECK="true"
            shift 1
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
if [ -n "$RUN_NAME" ]; then
    :
elif [ -n "$PROVIDER" ] || [ -n "$MODEL" ] || [ -n "$PROMOTION_MODE" ]; then
    [ -n "$PROVIDER" ] || die "--provider is required when using run-name convention"
    [ -n "$MODEL" ] || die "--model is required when using run-name convention"
    [ -n "$PROMOTION_MODE" ] || die "--promotion-mode is required when using run-name convention"
    MODEL_TAG="${MODEL//\//-}"
    RUN_NAME="goodai__smoke5__provider=${PROVIDER}__model=${MODEL_TAG}__promotion=${PROMOTION_MODE}__agent=${AGENT_TYPE}__${AGENT_VARIANT}__${STAMP}"
else
    RUN_NAME="${RUN_NAME_BASE}__${AGENT_TYPE}__${AGENT_VARIANT}__${STAMP}"
fi

echo -e "${BLUE}=== GoodAI LTM Benchmark (MAS remote) ===${NC}"
echo "AGENT_URL:      $AGENT_URL"
echo "agent_type:     $AGENT_TYPE"
echo "agent_variant:  $AGENT_VARIANT"
echo "run_name:       $RUN_NAME"
echo "config:         $CONFIG_PATH"
echo ""

cd "$BENCH_ROOT"

function provider_check() {
    local base_url="$AGENT_URL"
    if [[ "$base_url" == */v1/chat/completions ]]; then
        base_url="${base_url%/v1/chat/completions}"
    fi

    echo -e "${BLUE}Provider check: /health${NC}"
    local health_json
    health_json="$(curl -4 -sS "$base_url/health")"
    HEALTH_JSON="$health_json" "$BENCH_PYTHON" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["HEALTH_JSON"])
required = ["status", "agent_type", "agent_variant", "redis"]
missing = [k for k in required if k not in payload]
if missing:
    print(f"Missing /health fields: {missing}", file=sys.stderr)
    sys.exit(2)
if payload.get("status") != "ok":
    print(f"/health status is not ok: {payload.get('status')}", file=sys.stderr)
    sys.exit(2)
PY

    echo -e "${BLUE}Provider check: single-turn metadata${NC}"
    local vis_session
    vis_session="parity-check-${STAMP}"
    local ping_json
    ping_json="$(curl -4 -sS "$AGENT_URL" \
        -H 'Content-Type: application/json' \
        -H "X-Session-Id: ${vis_session}" \
        -d '{"model":"default","messages":[{"role":"user","content":"Reply with exactly: pong"}]}')"
    PING_JSON="$ping_json" VIS_SESSION="$vis_session" "$BENCH_PYTHON" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["PING_JSON"])
metadata = payload.get("metadata") or {}
required = [
    "llm_provider",
    "llm_model",
    "llm_ms",
    "storage_ms",
    "client_session_id",
    "yaam_session_id",
    "promotion_mode",
    "promotion_status",
]
missing = [k for k in required if k not in metadata]
if missing:
    print(f"Missing metadata fields: {missing}", file=sys.stderr)
    sys.exit(2)

context = metadata.get("context") or {}
context_required = [
    "recent_turns_count",
    "working_facts_count",
    "episodic_chunks_count",
    "semantic_knowledge_count",
]
context_missing = [k for k in context_required if k not in context]
if context_missing:
    print(f"Missing context fields: {context_missing}", file=sys.stderr)
    sys.exit(2)

vis_session = os.environ["VIS_SESSION"]
if metadata.get("client_session_id") != vis_session:
    print("client_session_id does not match X-Session-Id", file=sys.stderr)
    sys.exit(2)
PY
}

if [ "$SKIP_PROVIDER_CHECK" != "true" ]; then
    provider_check
fi

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

REPORT_DIR="$BENCH_ROOT/data/reports"
REPORT_MATCHES=("$REPORT_DIR"/*"$RUN_NAME"*.html)
if [ ${#REPORT_MATCHES[@]} -eq 0 ]; then
    echo -e "${YELLOW}Warning:${NC} no HTML report found for run name in $REPORT_DIR"
else
    echo "HTML report:"
    echo "  ${REPORT_MATCHES[0]}"
fi
