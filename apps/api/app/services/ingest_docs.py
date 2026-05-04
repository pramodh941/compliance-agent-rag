import os
import uuid
from datetime import datetime

from app.services.document_router import route_document
from app.services.chunker import chunk_text
from app.services.ollama_client import get_embedding
from app.dependencies.qdrant import get_qdrant_client

# 🔥 NEW
from app.services.hybrid_retriever import hybrid_retriever

COLLECTION_NAME = "sec_docs"


def ingest_sec_docs():
    client = get_qdrant_client()

    # recreate collection (dev mode)
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
    all_ids = []

    # 🔥 collect docs for BM25
    bm25_docs = []

    for file in all_files:
        path = os.path.join(base_path, file)

        pages = route_document(path, "pdf")

        total_chunks_file = 0

        for page in pages:
            page_text = page.get("text", "")
            page_number = page.get("metadata", {}).get("page_number")

            if not page_text.strip():
                continue

            chunks = chunk_text(page_text)
            total_chunks = len(chunks)

            for i, chunk in enumerate(chunks):
                print(f"{file} | Page {page_number} | Chunk {i+1}/{total_chunks}")

                vector = get_embedding(chunk)
                if vector is None:
                    print(f"⚠️ Skipping chunk (embedding failed)")
                    continue

                chunk_id = str(uuid.uuid4())

                payload = {
                    "text": chunk,
                    "source": file,
                    "doc_type": "sec",
                    "page": page_number,
                    "chunk_index": i,
                    "total_chunks": total_chunks,
                    "chunk_id": chunk_id,
                    "ingested_at": datetime.utcnow().isoformat(),
                    "title": file.replace(".pdf", "").replace("-", " "),
                    "section": "unknown",
                    "tags": []
                }

                all_vectors.append(vector)
                all_payloads.append(payload)
                all_ids.append(chunk_id)

                # 🔥 ADD TO BM25
                bm25_docs.append({
                    "text": chunk,
                    "source": file,
                    "page": page_number,
                    "doc_type": "sec"
                })

                total_chunks_file += 1

        print(f"{file} → total chunks: {total_chunks_file}")

    # 🔥 BUILD BM25 INDEX
    print("[Hybrid] Building BM25 index...")
    hybrid_retriever.add_documents(bm25_docs)
    print(f"[Hybrid] BM25 loaded with {len(bm25_docs)} chunks")

    # upload to Qdrant
    client.upload_collection(
        collection_name=COLLECTION_NAME,
        vectors=all_vectors,
        payload=all_payloads,
        ids=all_ids
    )

    return {
        "status": "sec_docs_indexed",
        "files": len(all_files),
        "chunks": len(all_vectors)
    }