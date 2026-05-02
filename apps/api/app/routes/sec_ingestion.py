from fastapi import APIRouter
from app.services.ingest_docs import ingest_sec_docs

router = APIRouter()

@router.post("/ingest-sec-docs")
def run():
    return ingest_sec_docs()