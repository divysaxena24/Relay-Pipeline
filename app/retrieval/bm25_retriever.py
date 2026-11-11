
import re
from typing import Any

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    """
    Convert text into lowercase searchable terms.
    Example:
    'Scaled Dot-Product Attention'
    -> ['scaled', 'dot', 'product', 'attention']
    """
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


class BM25Retriever:
    def __init__(self, chunks: list[dict[str, Any]]):
        if not chunks:
            raise ValueError("Cannot create BM25 index: chunks are empty.")

        self.chunks = chunks

        # Convert every chunk into a list of searchable terms.
        self.tokenized_corpus = [
            tokenize(chunk["text"])
            for chunk in chunks
        ]

        # Build the BM25 index.
        self.index = BM25Okapi(self.tokenized_corpus)

        print(f"BM25 index created with {len(chunks)} chunks.")

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> list[dict[str, Any]]:

        if not query.strip():
            raise ValueError("Search query cannot be empty.")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        # Calculate BM25 relevance scores for every chunk.
        scores = self.index.get_scores(query_tokens)

        # Sort chunks by relevance score, highest first.
        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )

        results = []

        for index in ranked_indices:
            score = float(scores[index])

            # Ignore chunks with no matching query terms.
            if score <= 0:
                continue

            result = self.chunks[index].copy()
            result["score"] = round(score, 4)

            results.append(result)

            if len(results) == top_k:
                break

        return results
