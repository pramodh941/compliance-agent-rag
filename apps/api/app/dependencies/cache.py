from app.services.cache import SimpleTTLCache

# Embedding cache (longer TTL)
embedding_cache = SimpleTTLCache(ttl_seconds=3600)

# Retrieval / response cache (short TTL)
retrieval_cache = SimpleTTLCache(ttl_seconds=300)