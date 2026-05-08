# OLD PDF Ingestion Service - Kept for reference, not used in current implementation

import os
from pypdf import PdfReader
from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding

COLLECTION = "sec_docs"


def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text, size=800):
    words = text.split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]


def ingest_sec_docs():
    client = get_qdrant_client()

    folder = "app/data/sec"
    all_chunks = []

    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            path = os.path.join(folder, file)
            text = extract_text(path)
            chunks = chunk_text(text)
            all_chunks.extend(chunks)

    if not all_chunks:
        return {"status": "no_documents_found"}

    vectors = [get_embedding(c) for c in all_chunks]

    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config={"size": 768, "distance": "Cosine"}
    )

    client.upload_collection(
        collection_name=COLLECTION,
        vectors=vectors,
        payload=[{"text": c} for c in all_chunks]
    )

    return {
        "status": "sec_docs_indexed",
        "chunks": len(all_chunks)
    }