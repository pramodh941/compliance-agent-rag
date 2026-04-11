from qdrant_client import QdrantClient

def get_qdrant_client():
    client = QdrantClient(
        host="qdrant",
        port=6333
    )
    return client