from rank_bm25 import BM25Okapi


class HybridRetriever:
    def __init__(self):
        self.corpus = []
        self.tokenized_corpus = []
        self.metadata = []
        self.bm25 = None

    def add_documents(self, docs: list[dict]):
        """
        docs = [
            {
                "text": "...",
                "source": "...",
                "page": ...
            }
        ]
        """

        for d in docs:
            tokens = d["text"].lower().split()

            self.corpus.append(d["text"])
            self.tokenized_corpus.append(tokens)
            self.metadata.append(d)

        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, k=5):
        if not self.bm25:
            return []

        tokenized_query = query.lower().split()

        scores = self.bm25.get_scores(tokenized_query)

        top_idx = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:k]

        return [self.metadata[i] for i in top_idx]

hybrid_retriever = HybridRetriever()