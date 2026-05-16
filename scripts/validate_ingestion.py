#!/usr/bin/env python3
"""
Ingestion validation and smoke test script.

Validates the ingestion pipeline, parser configuration, and basic functionality.
"""
import os
import sys
import argparse
import time

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

# Robust dotenv import with fallback for local/Docker compatibility
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available - continue without it
    # (environment variables should be set elsewhere)
    pass

from app.core.ingestion_config import IngestionConfig
from app.services.document_parser import DocumentParser


def validate_config():
    """Validate ingestion configuration."""
    print("=== Validating Ingestion Configuration ===")
    config = IngestionConfig()
    
    # Check profile
    profile = config.get_profile()
    print(f"Profile: {profile}")
    
    # Validate configuration
    is_valid = config.validate()
    
    if is_valid:
        print("✓ Configuration is valid")
    else:
        print("⚠ Configuration has warnings (see logs)")
    
    # Display summary
    summary = config.get_summary()
    print(f"\nChunking Strategy: {summary['chunking']['strategy']}")
    print(f"Chunk Size: {summary['chunking']['chunk_size']}")
    print(f"PDF Parser: {summary['parsing']['pdf_parser']}")
    print(f"\nFeature Toggles:")
    for feature, enabled in summary['features'].items():
        status = "✓" if enabled else "✗"
        print(f"  {status} {feature}")
    
    return is_valid


def validate_parser():
    """Validate parser initialization and fallback."""
    print("\n=== Validating Parser ===")
    
    try:
        config = IngestionConfig()
        parser = DocumentParser(config)
        
        print(f"✓ Parser initialized successfully")
        print(f"  Parser type: {parser.parser_type}")
        print(f"  Chunking strategy: {config.CHUNKING_STRATEGY}")
        
        return True
    except Exception as e:
        print(f"✗ Parser initialization failed: {e}")
        return False


def validate_chunking():
    """Validate chunking with sample text."""
    print("\n=== Validating Chunking ===")
    
    try:
        config = IngestionConfig()
        parser = DocumentParser(config)
        
        # Sample text
        sample_text = """
        This is a sample document with multiple sections.
        
        SECTION 1: INTRODUCTION
        This section provides an introduction to the document.
        It contains important information about the topic.
        
        SECTION 2: MAIN CONTENT
        This section contains the main content of the document.
        It includes detailed information and examples.
        """
        
        from app.services.document_parser import DocumentMetadata
        metadata = DocumentMetadata(title="Sample Document")
        
        chunks = parser._simple_chunking(sample_text, metadata, "sample.pdf", "policy")
        
        if chunks:
            print(f"✓ Chunking successful")
            print(f"  Chunks created: {len(chunks)}")
            print(f"  First chunk length: {len(chunks[0].text)}")
            print(f"  First chunk metadata: {list(chunks[0].metadata.keys())}")
            return True
        else:
            print("✗ No chunks created")
            return False
            
    except Exception as e:
        print(f"✗ Chunking validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_metadata_extraction():
    """Validate metadata extraction."""
    print("\n=== Validating Metadata Extraction ===")
    
    try:
        config = IngestionConfig()
        
        # Check metadata extraction flags
        print(f"Extract Title: {config.EXTRACT_TITLE}")
        print(f"Extract Author: {config.EXTRACT_AUTHOR}")
        print(f"Extract Date: {config.EXTRACT_DATE}")
        print(f"Extract Page Numbers: {config.EXTRACT_PAGE_NUMBERS}")
        print(f"Extract Section Headers: {config.EXTRACT_SECTION_HEADERS}")
        
        print("✓ Metadata extraction configuration validated")
        return True
        
    except Exception as e:
        print(f"✗ Metadata extraction validation failed: {e}")
        return False


def validate_dependencies():
    """Validate required dependencies."""
    print("\n=== Validating Dependencies ===")
    
    dependencies = {
        "pypdf": "pypdf",
        "qdrant-client": "qdrant_client",
        "requests": "requests",
        "fastapi": "fastapi"
    }
    
    missing = []
    for package, import_name in dependencies.items():
        try:
            __import__(import_name)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\n⚠ Missing dependencies: {', '.join(missing)}")
        return False
    else:
        print("\n✓ All required dependencies installed")
        return True


def run_smoke_test():
    """Run basic smoke test of ingestion pipeline."""
    print("\n=== Running Smoke Test ===")
    
    try:
        config = IngestionConfig()
        parser = DocumentParser(config)
        
        # Test with sample text
        sample_text = "This is a test document for smoke testing the ingestion pipeline."
        from app.services.document_parser import DocumentMetadata
        metadata = DocumentMetadata(title="Smoke Test Document")
        
        chunks = parser._simple_chunking(sample_text, metadata, "smoke_test.pdf", "policy")
        
        if chunks and len(chunks) > 0:
            print(f"✓ Smoke test passed")
            print(f"  Created {len(chunks)} chunk(s)")
            return True
        else:
            print("✗ Smoke test failed - no chunks created")
            return False
            
    except Exception as e:
        print(f"✗ Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Validate ingestion pipeline")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full validation including smoke test"
    )
    
    args = parser.parse_args()
    
    print("=== Ingestion Validation ===\n")
    
    results = []
    
    # Always run basic validations
    results.append(("Configuration", validate_config()))
    results.append(("Dependencies", validate_dependencies()))
    results.append(("Parser", validate_parser()))
    results.append(("Chunking", validate_chunking()))
    results.append(("Metadata Extraction", validate_metadata_extraction()))
    
    # Run smoke test if requested
    if args.full:
        results.append(("Smoke Test", run_smoke_test()))
    
    # Summary
    print("\n=== Validation Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("✓ All validations passed")
        return 0
    else:
        print(f"✗ {total - passed} validation(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
