from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.improved_ingestion_service import get_ingestion_service
from app.core.ingestion_config import IngestionConfig
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class IngestionRequest(BaseModel):
    directory: str
    collection_name: str
    doc_type: str = "policy"
    recreate_collection: bool = True


@router.post("/ingest")
def run_ingestion(request: IngestionRequest, background_tasks: BackgroundTasks):
    """
    Ingest documents from a directory into Qdrant.
    
    This endpoint processes PDF documents using the improved ingestion pipeline
    with configurable parsing, chunking, and metadata extraction.
    """
    try:
        service = get_ingestion_service()
        result = service.ingest_directory(
            directory=request.directory,
            collection_name=request.collection_name,
            doc_type=request.doc_type,
            recreate_collection=request.recreate_collection
        )
        return result
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/status")
def get_ingestion_status():
    """Get current ingestion status and configuration."""
    try:
        service = get_ingestion_service()
        return service.get_ingestion_status()
    except Exception as e:
        logger.error(f"Failed to get ingestion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/config")
def get_ingestion_config():
    """Get current ingestion configuration."""
    try:
        config = IngestionConfig()
        return config.get_summary()
    except Exception as e:
        logger.error(f"Failed to get ingestion config: {e}")
        raise HTTPException(status_code=500, detail=str(e))