from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding
from app.services.hybrid_retriever import hybrid_retriever

COLLECTION_NAME = "policies"

def index_policies():
    client = get_qdrant_client()

    # recreate collection
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "size": 768,   # nomic-embed-text dimension
            "distance": "Cosine"
        }
    )

    # read policies
    with open("app/data/policies.txt", "r") as f:
        text = f.read()

    # simple chunking
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]

    # 🔥 Build BM25 index for policies
    bm25_docs = [{"text": c, "doc_type": "policy"} for c in chunks]

    print("[Hybrid] Building BM25 index for policies...")
    hybrid_retriever.add_documents(bm25_docs)
    print(f"[Hybrid] BM25 loaded with {len(bm25_docs)} policy chunks")

    # generate embeddings via Ollama
    vectors = [get_embedding(chunk) for chunk in chunks]

    # upload to Qdrant
    client.upload_collection(
        collection_name=COLLECTION_NAME,
        vectors=vectors,
        payload=[{"text": c} for c in chunks]
    )

    return {
        "status": "policies_indexed",
        "chunks": len(chunks)
    }