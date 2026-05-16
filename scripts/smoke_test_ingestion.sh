#!/bin/bash
# Smoke test script for ingestion pipeline

set -e

echo "=== Ingestion Smoke Test ==="
echo ""

# Test 1: Configuration validation
echo "Test 1: Configuration validation"
python3 scripts/validate_ingestion.py
if [ $? -ne 0 ]; then
    echo "✗ Configuration validation failed"
    exit 1
fi
echo "✓ Configuration validation passed"
echo ""

# Test 2: Ingestion config endpoint
echo "Test 2: Ingestion config endpoint"
curl -s http://localhost:8000/ingest/config > /dev/null
if [ $? -ne 0 ]; then
    echo "✗ Ingestion config endpoint failed"
    exit 1
fi
echo "✓ Ingestion config endpoint passed"
echo ""

# Test 3: Diagnostics endpoint
echo "Test 3: Diagnostics endpoint"
curl -s http://localhost:8000/diagnostics > /dev/null
if [ $? -ne 0 ]; then
    echo "✗ Diagnostics endpoint failed"
    exit 1
fi
echo "✓ Diagnostics endpoint passed"
echo ""

# Test 4: Ingestion status endpoint
echo "Test 4: Ingestion status endpoint"
curl -s http://localhost:8000/ingest/status > /dev/null
if [ $? -ne 0 ]; then
    echo "✗ Ingestion status endpoint failed"
    exit 1
fi
echo "✓ Ingestion status endpoint passed"
echo ""

echo "=== All Smoke Tests Passed ==="
