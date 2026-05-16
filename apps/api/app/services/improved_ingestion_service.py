"""
Improved document ingestion service with better parsing, metadata extraction, and error handling.

Provides a unified ingestion pipeline with support for multiple PDF parsers,
optional OCR, configurable chunking strategies, and comprehensive logging.
"""
import os
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from qdrant_client.models import PointStruct
from app.core.ingestion_config import IngestionConfig
from app.services.document_parser import DocumentParser, DocumentChunk, DocumentMetadata
from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding
from app.core.logging import get_logger

logger = get_logger(__name__)


class IngestionMetrics:
    """Metrics for ingestion operations."""
    
    def __init__(self):
        self.documents_processed = 0
        self.documents_failed = 0
        self.chunks_created = 0
        self.chunks_failed = 0
        self.embeddings_generated = 0
        self.embeddings_failed = 0
        self.total_time_ms = 0
        self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "documents_processed": self.documents_processed,
            "documents_failed": self.documents_failed,
            "chunks_created": self.chunks_created,
            "chunks_failed": self.chunks_failed,
            "embeddings_generated": self.embeddings_generated,
            "embeddings_failed": self.embeddings_failed,
            "total_time_ms": self.total_time_ms,
            "success_rate": self.documents_processed / (self.documents_processed + self.documents_failed) if (self.documents_processed + self.documents_failed) > 0 else 0,
            "errors": self.errors[:10]  # Limit to last 10 errors
        }


class ImprovedIngestionService:
    """Improved ingestion service with better parsing and error handling."""
    
    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config or IngestionConfig()
        self.parser = DocumentParser(self.config)
        self.metrics = IngestionMetrics()
    
    def ingest_directory(
        self,
        directory: str,
        collection_name: str,
        doc_type: str = "policy",
        recreate_collection: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest all documents from a directory.
        
        Args:
            directory: Path to directory containing documents
            collection_name: Qdrant collection name
            doc_type: Type of documents (policy, sec_doc, etc.)
            recreate_collection: Whether to recreate the collection
            
        Returns:
            Ingestion results with metrics
        """
        start_time = time.time()
        logger.info(f"Starting ingestion from directory: {directory}")
        
        # Get all PDF files
        directory_path = Path(directory)
        if not directory_path.exists():
            error_msg = f"Directory not found: {directory}"
            logger.error(error_msg)
            self.metrics.errors.append(error_msg)
            return {"status": "error", "message": error_msg, "metrics": self.metrics.to_dict()}
        
        pdf_files = list(directory_path.glob("*.pdf"))
        if not pdf_files:
            error_msg = f"No PDF files found in {directory}"
            logger.warning(error_msg)
            return {"status": "no_documents", "message": error_msg, "metrics": self.metrics.to_dict()}
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each document
        all_chunks = []
        for pdf_file in pdf_files:
            try:
                result = self.ingest_document(
                    str(pdf_file),
                    collection_name,
                    doc_type,
                    recreate_collection=False  # Don't recreate for each doc
                )

                if isinstance(result, tuple):
                    chunks = result[0]
                else:
                    chunks = result or []

                logger.info(
                    "Document ingest result type",
                    extra={
                        "operation": "ingestion",
                        "file": str(pdf_file),
                        "result_type": type(result).__name__,
                        "chunks_returned": len(chunks) if isinstance(chunks, list) else None
                    }
                )

                all_chunks.extend(chunks)
                self.metrics.documents_processed += 1
            except Exception as e:
                error_msg = f"Failed to process {pdf_file.name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.metrics.errors.append(error_msg)
                self.metrics.documents_failed += 1
        
        # Create or recreate collection
        qdrant = get_qdrant_client()
        if recreate_collection:
            logger.info(f"Recreating collection: {collection_name}")
            try:
                qdrant.recreate_collection(
                    collection_name=collection_name,
                    vectors_config={"size": 768, "distance": "Cosine"}
                )
            except Exception as e:
                logger.error(f"Failed to recreate collection: {e}")
                return {"status": "error", "message": str(e), "metrics": self.metrics.to_dict()}
        
        # Generate embeddings and upload
        if all_chunks:
            self._upload_chunks(all_chunks, collection_name, qdrant)
        
        self.metrics.total_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Ingestion completed",
            extra={
                "operation": "ingestion",
                "documents_processed": self.metrics.documents_processed,
                "documents_failed": self.metrics.documents_failed,
                "chunks_created": self.metrics.chunks_created,
                "total_time_ms": round(self.metrics.total_time_ms, 2)
            }
        )
        
        return {
            "status": "completed",
            "collection": collection_name,
            "metrics": self.metrics.to_dict()
        }
    
    def ingest_document(
        self,
        file_path: str,
        collection_name: str,
        doc_type: str = "policy",
        recreate_collection: bool = False
    ) -> List[DocumentChunk]:
        """
        Ingest a single document.
        
        Args:
            file_path: Path to the document file
            collection_name: Qdrant collection name
            doc_type: Type of document
            recreate_collection: Whether to recreate the collection
            
        Returns:
            List of document chunks
        """
        logger.info(f"Processing document: {file_path}", extra={"operation": "ingestion", "file": file_path})
        
        try:
            # Parse document
            chunks, metadata = self.parser.parse_document(file_path, doc_type)
            
            if not chunks:
                logger.warning(f"No chunks extracted from {file_path}", extra={"operation": "document_parsing", "file": file_path, "chunks": 0})
                return []
            
            logger.info(
                f"Extracted {len(chunks)} chunks from {file_path}",
                extra={
                    "operation": "document_parsing",
                    "file": file_path,
                    "chunks": len(chunks),
                    "page_count": metadata.page_count,
                    "title": metadata.title,
                    "parser_type": self.parser.parser_type
                }
            )
            
            # Upload to Qdrant if collection specified
            if collection_name:
                qdrant = get_qdrant_client()
                if recreate_collection:
                    try:
                        qdrant.recreate_collection(
                            collection_name=collection_name,
                            vectors_config={"size": 768, "distance": "Cosine"}
                        )
                        logger.info(f"Recreated collection: {collection_name}", extra={"operation": "ingestion", "collection": collection_name})
                    except Exception as e:
                        logger.error(f"Failed to recreate collection: {e}", extra={"operation": "ingestion", "collection": collection_name})
                
                self._upload_chunks(chunks, collection_name, qdrant, file_path)
            
            return chunks
        except Exception as e:
            logger.error(f"Failed to ingest document {file_path}: {e}", extra={"operation": "ingestion", "file": file_path}, exc_info=True)
            raise
    
    def _upload_chunks(
        self,
        chunks: List[DocumentChunk],
        collection_name: str,
        qdrant_client,
        source_file: Optional[str] = None
    ):
        """Upload chunks to Qdrant with embeddings."""
        logger.info(
            f"Uploading {len(chunks)} chunks to collection: {collection_name}",
            extra={
                "operation": "chunk_upload",
                "collection": collection_name,
                "chunks": len(chunks),
                "source_file": source_file
            }
        )
        
        # Generate embeddings in batches
        batch_size = self.config.EMBEDDING_BATCH_SIZE
        vectors = []
        payloads = []
        
        for i, chunk in enumerate(chunks):
            try:
                embedding = get_embedding(chunk.text)
                if embedding:
                    vectors.append(embedding)
                    payloads.append({
                        "text": chunk.text,
                        "source": chunk.source,
                        "page": chunk.page_number,
                        "doc_type": chunk.doc_type,
                        "chunk_index": chunk.chunk_index,
                        **chunk.metadata
                    })
                    self.metrics.embeddings_generated += 1
                else:
                    logger.warning(f"Failed to generate embedding for chunk {i}", extra={"operation": "embedding_generation", "chunk_index": i, "success": False})
                    self.metrics.embeddings_failed += 1
            except Exception as e:
                logger.error(f"Error generating embedding for chunk {i}: {e}", extra={"operation": "embedding_generation", "chunk_index": i, "success": False})
                self.metrics.embeddings_failed += 1
            
            # Upload in batches
            if len(vectors) >= batch_size:
                self._upload_batch(vectors, payloads, collection_name, qdrant_client)
                vectors = []
                payloads = []
        
        # Upload remaining chunks
        if vectors:
            self._upload_batch(vectors, payloads, collection_name, qdrant_client)
        
        self.metrics.chunks_created = len(chunks)
        logger.info(
            f"Upload complete: {self.metrics.embeddings_generated} embeddings generated",
            extra={
                "operation": "chunk_upload",
                "collection": collection_name,
                "embeddings_generated": self.metrics.embeddings_generated,
                "embeddings_failed": self.metrics.embeddings_failed
            }
        )
    
    def _upload_batch(self, vectors, payloads, collection_name, qdrant_client):
        """Upload a batch of vectors to Qdrant."""
        try:
            points = [
                PointStruct(
                    id=idx,
                    vector=vector,
                    payload=payload
                )
                for idx, (vector, payload) in enumerate(zip(vectors, payloads))
            ]
            qdrant_client.upload_points(
                collection_name=collection_name,
                points=points
            )
            logger.info(
                f"Uploaded batch of {len(vectors)} vectors",
                extra={
                    "operation": "batch_upload",
                    "collection": collection_name,
                    "batch_size": len(vectors),
                    "success": True
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to upload batch: {e}",
                extra={
                    "operation": "batch_upload",
                    "collection": collection_name,
                    "batch_size": len(vectors),
                    "success": False
                }
            )
            self.metrics.errors.append(f"Batch upload failed: {str(e)}")
    
    def get_ingestion_status(self) -> Dict[str, Any]:
        """Get current ingestion status and metrics."""
        return {
            "config": self.config.get_summary(),
            "metrics": self.metrics.to_dict(),
            "parser_type": self.parser.parser_type
        }


# Singleton instance
_ingestion_service = None


def get_ingestion_service() -> ImprovedIngestionService:
    """Get the singleton ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = ImprovedIngestionService()
    return _ingestion_service
