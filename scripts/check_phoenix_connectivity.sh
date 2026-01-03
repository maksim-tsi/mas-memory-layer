#!/usr/bin/env bash
# scripts/check_phoenix_connectivity.sh - Verify Arize Phoenix connectivity
#
# Usage: ./scripts/check_phoenix_connectivity.sh
#
# Environment variables (optional, defaults shown):
#   DEV_NODE_IP=192.168.107.172
#   PHOENIX_PORT=6006
#   PHOENIX_GRPC_PORT=4317

set -euo pipefail

# Configuration with defaults
PHOENIX_HOST="${DEV_NODE_IP:-192.168.107.172}"
PHOENIX_HTTP_PORT="${PHOENIX_PORT:-6006}"
PHOENIX_GRPC_PORT="${PHOENIX_GRPC_PORT:-4317}"

echo "============================================="
echo "  Arize Phoenix Connectivity Check"
echo "============================================="
echo ""
echo "Target Host: ${PHOENIX_HOST}"
echo ""

# Check HTTP endpoint (UI + OTLP HTTP collector)
echo -n "HTTP UI (port ${PHOENIX_HTTP_PORT}): "
if curl -sf "http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}" -o /dev/null 2>/dev/null; then
    echo "✅ OK"
    HTTP_OK=true
else
    echo "❌ FAILED"
    HTTP_OK=false
fi

# Check gRPC endpoint (optional, may not be exposed)
echo -n "gRPC Collector (port ${PHOENIX_GRPC_PORT}): "
if nc -z "${PHOENIX_HOST}" "${PHOENIX_GRPC_PORT}" 2>/dev/null; then
    echo "✅ OK"
    GRPC_OK=true
else
    echo "⚠️  Not reachable (may not be exposed)"
    GRPC_OK=false
fi

echo ""
echo "============================================="
echo "  Collector Endpoints"
echo "============================================="
echo ""
echo "OTLP HTTP: http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}/v1/traces"
echo "OTLP gRPC: ${PHOENIX_HOST}:${PHOENIX_GRPC_PORT}"
echo ""

echo "============================================="
echo "  Environment Configuration"
echo "============================================="
echo ""
echo "Add to your .env file:"
echo ""
echo "  # Arize Phoenix LLM Observability"
echo "  PHOENIX_COLLECTOR_ENDPOINT=http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}/v1/traces"
echo "  PHOENIX_PROJECT_NAME=mlm-mas-dev"
echo ""

echo "============================================="
echo "  Project Naming Convention"
echo "============================================="
echo ""
echo "  Environment    | Project Name"
echo "  ---------------|---------------"
echo "  Development    | mlm-mas-dev"
echo "  Testing/CI     | mlm-mas-test"
echo "  Production     | mlm-mas-prod"
echo ""

# Summary
echo "============================================="
echo "  Summary"
echo "============================================="
echo ""
if [ "$HTTP_OK" = true ]; then
    echo "✅ Phoenix is reachable via HTTP"
    echo "   Open UI: http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}"
    echo ""
    echo "To enable tracing in your application:"
    echo "  export PHOENIX_COLLECTOR_ENDPOINT=http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}/v1/traces"
    echo "  export PHOENIX_PROJECT_NAME=mlm-mas-dev"
    exit 0
else
    echo "❌ Phoenix HTTP endpoint not reachable"
    echo "   Verify Phoenix is running: docker ps | grep phoenix"
    echo "   Check firewall rules for port ${PHOENIX_HTTP_PORT}"
    exit 1
fi
