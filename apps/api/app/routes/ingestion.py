from fastapi import APIRouter
from app.services.ingestion_service import ingest_emails

router = APIRouter()

@router.post("/ingest")
def run_ingestion():
    return ingest_emails()