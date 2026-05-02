import os
from app.services.document_router import route_document
from app.services.chunker import chunk_text
from app.services.ollama_client import get_embedding
from app.dependencies.qdrant import get_qdrant_client

COLLECTION_NAME = "sec_docs"


def ingest_sec_docs():
    client = get_qdrant_client()

    # ensure collection exists (safe recreate for dev)
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "size": 768,
            "distance": "Cosine"
        }
    )

    base_path = "app/data/sec"
    all_files = [f for f in os.listdir(base_path) if f.endswith(".pdf")]

    all_vectors = []
    all_payloads = []

    for file in all_files:
        path = os.path.join(base_path, file)

        # 1. extract text
        text = route_document(path, "pdf")

        # 2. chunk
        chunks = chunk_text(text)

        # 3. embed
        for chunk in chunks:
            vector = get_embedding(chunk)

            all_vectors.append(vector)
            all_payloads.append({
                "text": chunk,
                "source": file
            })

    # 4. upload to qdrant
    client.upload_collection(
        collection_name=COLLECTION_NAME,
        vectors=all_vectors,
        payload=all_payloads
    )

    return {
        "status": "sec_docs_indexed",
        "files": len(all_files),
        "chunks": len(all_vectors)
    }