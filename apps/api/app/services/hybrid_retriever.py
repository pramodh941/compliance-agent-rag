"""
Hybrid retriever combining BM25 keyword search with metadata filtering and policy-aware ranking.

Improves retrieval quality by:
- Filtering results by doc_type and collection
- Keyword prioritization (MNPI, insider trading, etc.)
- Title-aware retrieval
- Metadata-based score boosting
"""
import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


# Policy-specific keywords for keyword weighting
POLICY_KEYWORDS = {
    "mnpi": ["mnpi", "insider trading", "material nonpublic", "non-public information"],
    "compliance": ["compliance", "regulatory", "policy", "requirement", "procedure"],
    "communication": ["communication", "disclosure", "announce", "public"],
    "ethics": ["ethics", "conduct", "integrity", "conflict of interest"],
    "trading": ["trading", "transaction", "buy", "sell", "investment"],
    "security": ["security", "confidential", "classified", "restricted"],
}


class HybridRetriever:
    """Hybrid retriever combining BM25 with metadata filtering and policy-aware ranking."""
    
    def __init__(self):
        self.corpus = []
        self.tokenized_corpus = []
        self.metadata = []
        self.bm25 = None
        self.logger = logging.getLogger(__name__)

    def add_documents(self, docs: List[Dict[str, Any]]):
        """
        Add documents to the retriever.
        
        Expected document format:
        {
            "text": "...",
            "source": "...",
            "page": ...,
            "doc_type": "policy|sec_doc|...",
            "title": "...",
            "collection": "policies|sec_docs|..."
        }
        """
        for d in docs:
            # Ensure required fields exist
            if "text" not in d or not d["text"].strip():
                self.logger.warning(f"Skipping document with missing or empty text: {d.get('source', 'unknown')}")
                continue
                
            tokens = d["text"].lower().split()
            
            self.corpus.append(d["text"])
            self.tokenized_corpus.append(tokens)
            
            # Preserve all metadata
            self.metadata.append({
                "text": d["text"],
                "source": d.get("source", "unknown"),
                "page": d.get("page", 0),
                "doc_type": d.get("doc_type", "unknown"),
                "title": d.get("title", "untitled"),
                "collection": d.get("collection", "default"),
                "chunk_index": d.get("chunk_index", 0)
            })

        # Rebuild BM25 index
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            self.logger.info(f"BM25 index built with {len(self.corpus)} documents")

    def search(self, query: str, k: int = 5, doc_type: Optional[str] = None, collection: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using hybrid retrieval.
        
        Args:
            query: Search query
            k: Number of results to return
            doc_type: Optional filter by document type (policy, sec_doc, etc.)
            collection: Optional filter by collection name
            
        Returns:
            List of matching documents with metadata
        """
        if not self.bm25:
            self.logger.debug("BM25 index not initialized")
            return []

        tokenized_query = query.lower().split()
        
        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(tokenized_query)
        
        # Apply metadata filters and boost scores
        scored_results = []
        for i, score in enumerate(scores):
            if i >= len(self.metadata):
                continue
                
            doc_meta = self.metadata[i]
            
            # Apply doc_type filter if specified
            if doc_type and doc_meta.get("doc_type") != doc_type:
                continue
            
            # Apply collection filter if specified
            if collection and doc_meta.get("collection") != collection:
                continue
            
            # Boost score for keyword matches
            boosted_score = score
            
            # Check for policy-specific keyword matches
            for policy_type, keywords in POLICY_KEYWORDS.items():
                if any(kw in query.lower() for kw in keywords):
                    # Boost if document contains these keywords
                    if any(kw in doc_meta.get("text", "").lower() for kw in keywords):
                        boosted_score *= 1.3
                    
                    # Extra boost for title match
                    if any(kw in doc_meta.get("title", "").lower() for kw in keywords):
                        boosted_score *= 1.5
            
            scored_results.append((i, boosted_score, doc_meta))
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k results
        results = [meta for _, _, meta in scored_results[:k]]
        
        self.logger.debug(
            f"Retrieval query: '{query}' | Results: {len(results)} | "
            f"Filters: doc_type={doc_type}, collection={collection}"
        )
        
        return results

    def search_by_keywords(self, keywords: List[str], k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents by exact keyword matches.
        
        Args:
            keywords: List of keywords to search for
            k: Number of results to return
            
        Returns:
            List of matching documents
        """
        matching_docs = []
        
        for i, doc_meta in enumerate(self.metadata):
            text = doc_meta.get("text", "").lower()
            title = doc_meta.get("title", "").lower()
            
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw.lower() in text or kw.lower() in title)
            
            if matches > 0:
                matching_docs.append((i, matches, doc_meta))
        
        # Sort by match count
        matching_docs.sort(key=lambda x: x[1], reverse=True)
        
        return [meta for _, _, meta in matching_docs[:k]]


# Global instance
hybrid_retriever = HybridRetriever()