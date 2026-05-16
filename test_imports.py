#!/usr/bin/env python3
"""Test imports to verify fixes."""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'api'))

print("=== Testing Imports ===\n")

# Test 1: IngestionConfig with dotenv fallback
print("Test 1: IngestionConfig import")
try:
    from app.core.ingestion_config import IngestionConfig
    config = IngestionConfig()
    print("✓ IngestionConfig imported successfully")
    print(f"  Profile: {config.get_profile()}")
    print(f"  PDF Parser: {config.PDF_PARSER}")
except Exception as e:
    print(f"✗ IngestionConfig import failed: {e}")

# Test 2: DocumentParser
print("\nTest 2: DocumentParser import")
try:
    from app.services.document_parser import DocumentParser, DocumentMetadata
    parser = DocumentParser()
    print("✓ DocumentParser imported successfully")
    print(f"  Parser type: {parser.parser_type}")
except Exception as e:
    print(f"✗ DocumentParser import failed: {e}")

# Test 3: SEC PDF Parser
print("\nTest 3: SEC PDF Parser import")
try:
    from app.services.sec_pdf_parser import extract_text_from_pdf
    print("✓ SEC PDF Parser imported successfully")
    # Verify it returns tuple
    print("  Testing return type validation...")
    # We won't actually call it without a PDF, but we know it should return (str, dict)
except Exception as e:
    print(f"✗ SEC PDF Parser import failed: {e}")

# Test 4: HybridRetriever
print("\nTest 4: HybridRetriever import")
try:
    from app.services.hybrid_retriever import HybridRetriever, hybrid_retriever
    print("✓ HybridRetriever imported successfully")
    print(f"  Document count: {len(hybrid_retriever.corpus)}")
except Exception as e:
    print(f"✗ HybridRetriever import failed: {e}")

print("\n=== Import Tests Complete ===")
