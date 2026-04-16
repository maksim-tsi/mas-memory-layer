#!/bin/bash

# Script: healthcheck_v2.sh
# Purpose: Validate V2 memory endpoints and fail fast on 501 tier wiring regressions.
# Usage: ./scripts/healthcheck_v2.sh [BASE_URL]

set -e
set -u
set -o pipefail

BASE_URL="${1:-http://localhost:8080}"

probe_endpoint() {
    local label="$1"
    local endpoint="$2"
    local payload="$3"

    local status
    local response
    response=$(curl -sS -w "\n%{http_code}" \
        -H "Content-Type: application/json" \
        -X POST "${BASE_URL}${endpoint}" \
        -d "${payload}")
    status=$(echo "${response}" | tail -n 1)

    echo "[${label}] ${endpoint} -> HTTP ${status}"

    if [[ "${status}" == "501" ]]; then
        echo "[${label}] FAIL: received HTTP 501 Not Implemented"
        return 1
    fi

    if [[ "${status}" == "422" || "${status}" == "502" ]]; then
        echo "[${label}] PASS (partial): endpoint wired and reachable (HTTP ${status})"
        return 0
    fi

    if [[ "${status}" =~ ^2[0-9][0-9]$ ]]; then
        echo "[${label}] PASS: endpoint responded with success (HTTP ${status})"
        return 0
    fi

    echo "[${label}] FAIL: unexpected HTTP ${status}"
    return 1
}

main() {
    echo "Running V2 healthcheck against ${BASE_URL}"

    local failures=0

    probe_endpoint \
        "L2" \
        "/v2/memory/l2/facts" \
        '{"session_id":"healthcheck-session","agent_id":"healthcheck-agent","action":"retrieve"}' \
        || failures=$((failures + 1))

    probe_endpoint \
        "L3" \
        "/v2/memory/l3/query" \
        '{"session_id":"healthcheck-session","agent_id":"healthcheck-agent","nl_query":"healthcheck query"}' \
        || failures=$((failures + 1))

    if [[ ${failures} -gt 0 ]]; then
        echo "V2 healthcheck FAILED (${failures} failing probe(s))"
        exit 1
    fi

    echo "V2 healthcheck PASSED"
}

main "$@"
