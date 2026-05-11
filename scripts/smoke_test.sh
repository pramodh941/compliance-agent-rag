#!/bin/bash
# Smoke test script for compliance-agent-rag platform
# Tests basic functionality of all services

set -e

echo "=== Compliance Agent RAG Platform - Smoke Test ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local command="$2"
    
    echo -n "Testing: $test_name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAILED${NC}"
        ((FAILED++))
    fi
}

echo "--- Service Health Checks ---"
run_test "API Health" "curl -f http://localhost:8000/health"
run_test "Agent Worker Health" "curl -f http://localhost:8002/health"
run_test "MCP Server Health" "curl -f http://localhost:8001/health"
echo ""

echo "--- API Endpoints ---"
run_test "QA Endpoint" "curl -f -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{\"query\":\"test\"}'"
run_test "Compliance Scan" "curl -f -X POST http://localhost:8000/scan-email -H 'Content-Type: application/json' -d '{\"email_id\":\"1\"}'"
run_test "Alerts Endpoint" "curl -f http://localhost:8000/alerts?limit=10"
echo ""

echo "--- MCP Tools ---"
run_test "MCP Ping" "curl -f -X POST http://localhost:8001/mcp/ping -H 'Content-Type: application/json' -d '{}'"
run_test "MCP RAG Search" "curl -f -X POST http://localhost:8001/mcp/rag_search -H 'Content-Type: application/json' -d '{\"query\":\"test\"}'"
echo ""

echo "--- Summary ---"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some smoke tests failed!${NC}"
    exit 1
fi
