#!/usr/bin/env python3
"""
Improved document ingestion script with configuration support.

Usage:
    python scripts/ingest_docs_improved.py --directory app/data/sec --collection sec_docs
    python scripts/ingest_docs_improved.py --directory app/data/policies --collection policies
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

from app.services.improved_ingestion_service import get_ingestion_service
from app.core.ingestion_config import IngestionConfig


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into Qdrant")
    parser.add_argument(
        "--directory",
        required=True,
        help="Directory containing PDF documents"
    )
    parser.add_argument(
        "--collection",
        required=True,
        help="Qdrant collection name"
    )
    parser.add_argument(
        "--doc-type",
        default="policy",
        help="Document type (policy, sec_doc, etc.)"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate collection before ingestion"
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Show current configuration and exit"
    )
    
    args = parser.parse_args()
    
    # Show configuration if requested
    if args.config:
        config = IngestionConfig()
        print("=== Ingestion Configuration ===")
        print(f"Profile: {config.get_profile()}")
        print(f"Chunking Strategy: {config.CHUNKING_STRATEGY}")
        print(f"Chunk Size: {config.CHUNK_SIZE}")
        print(f"Overlap: {config.CHUNK_OVERLAP}")
        print(f"PDF Parser: {config.PDF_PARSER}")
        print(f"\nFeature Toggles:")
        print(f"  Layout Parsing: {config.ENABLE_LAYOUT_PARSING}")
        print(f"  OCR: {config.ENABLE_OCR}")
        print(f"  Table Extraction: {config.ENABLE_TABLE_EXTRACTION}")
        print(f"  Image Extraction: {config.ENABLE_IMAGE_EXTRACTION}")
        print(f"  Semantic Chunking: {config.ENABLE_SEMANTIC_CHUNKING}")
        print(f"  Hierarchy Detection: {config.ENABLE_HIERARCHY_DETECTION}")
        print(f"  Metadata Extraction: {config.ENABLE_METADATA_EXTRACTION}")
        return 0
    
    # Validate directory
    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found: {args.directory}")
        return 1
    
    # Run ingestion
    print(f"Starting ingestion from: {args.directory}")
    print(f"Target collection: {args.collection}")
    print(f"Document type: {args.doc_type}")
    
    start_time = time.time()
    
    try:
        service = get_ingestion_service()
        result = service.ingest_directory(
            directory=args.directory,
            collection_name=args.collection,
            doc_type=args.doc_type,
            recreate_collection=args.recreate
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n=== Ingestion Complete ===")
        print(f"Status: {result['status']}")
        print(f"Collection: {result.get('collection', 'N/A')}")
        print(f"Time: {elapsed:.2f}s")
        
        if 'metrics' in result:
            metrics = result['metrics']
            print(f"\n=== Metrics ===")
            print(f"Documents Processed: {metrics['documents_processed']}")
            print(f"Documents Failed: {metrics['documents_failed']}")
            print(f"Chunks Created: {metrics['chunks_created']}")
            print(f"Embeddings Generated: {metrics['embeddings_generated']}")
            print(f"Success Rate: {metrics['success_rate']:.1%}")
            
            if metrics['errors']:
                print(f"\n=== Errors ===")
                for error in metrics['errors']:
                    print(f"  - {error}")
        
        return 0 if result['status'] == 'completed' else 1
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
