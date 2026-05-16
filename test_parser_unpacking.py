#!/usr/bin/env python3
"""Test parser defensive unpacking."""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'api'))

from app.services.document_parser import DocumentParser, DocumentMetadata

print("=== Testing Parser Defensive Unpacking ===\n")

# Mock parser that returns invalid tuple
class MockParser(DocumentParser):
    def _extract_text_and_metadata(self, file_path):
        # Simulate the bug: return only text, not tuple
        return "Sample text content"

# Test with the mock parser
print("Test 1: Parser returning non-tuple (invalid)")
try:
    parser = MockParser()
    chunks, metadata = parser.parse_document("test.pdf", "policy")
    if not chunks:
        print("✓ Defensive unpacking handled invalid return correctly")
        print(f"  Empty chunks: {len(chunks) == 0}")
        print(f"  Metadata type: {type(metadata).__name__}")
    else:
        print("✗ Should have returned empty chunks for invalid parser output")
except Exception as e:
    print(f"✗ Exception raised: {e}")

# Test with normal parser that returns proper tuple
class GoodMockParser(DocumentParser):
    def _extract_text_and_metadata(self, file_path):
        metadata = DocumentMetadata()
        metadata.title = "Test Document"
        metadata.page_count = 1
        # Use longer text to meet MIN_TEXT_LENGTH requirement
        text = "Sample text content for chunking and processing. " * 10
        return text, metadata

print("\nTest 2: Parser returning proper tuple")
try:
    parser = GoodMockParser()
    chunks, metadata = parser.parse_document("test.pdf", "policy")
    if chunks and metadata.title == "Test Document":
        print("✓ Proper tuple unpacking works correctly")
        print(f"  Chunks created: {len(chunks)}")
        print(f"  Document title: {metadata.title}")
    else:
        print("✗ Should have created chunks for valid parser output")
except Exception as e:
    print(f"✗ Exception raised: {e}")

print("\n=== Parser Unpacking Tests Complete ===")
