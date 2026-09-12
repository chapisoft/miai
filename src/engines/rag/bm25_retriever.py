"""
BM25 Sparse Keyword Retriever.
Provides lexical matching for exact SKU codes, invoice numbers, tax IDs, and keywords.
"""

import math
import re
from typing import List, Dict, Tuple
from schemas.rag import DocumentChunk


class BM25Retriever:
    """In-memory BM25 retrieval algorithm for sparse keyword search."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: List[DocumentChunk] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple Vietnamese and English alphanumeric tokenizer."""
        return re.findall(r"\w+", text.lower())

    def index_documents(self, chunks: List[DocumentChunk]) -> None:
        """Builds BM25 index over a collection of document chunks."""
        self.corpus = chunks
        self.doc_lengths = []
        self.doc_freqs = {}

        total_length = 0
        for chunk in chunks:
            tokens = set(self.tokenize(chunk.content))
            doc_len = len(self.tokenize(chunk.content))
            self.doc_lengths.append(doc_len)
            total_length += doc_len

            for token in tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        num_docs = len(chunks)
        self.avg_doc_len = (total_length / num_docs) if num_docs > 0 else 0.0

        # Compute IDF
        self.idf = {}
        for token, freq in self.doc_freqs.items():
            self.idf[token] = math.log(1 + (num_docs - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        """Scores all indexed chunks against the query using BM25 formula."""
        if not self.corpus:
            return []

        query_tokens = self.tokenize(query)
        scores: List[Tuple[DocumentChunk, float]] = []

        for idx, chunk in enumerate(self.corpus):
            doc_tokens = self.tokenize(chunk.content)
            doc_len = self.doc_lengths[idx]
            score = 0.0

            # Term frequencies in document
            tf_map: Dict[str, int] = {}
            for t in doc_tokens:
                tf_map[t] = tf_map.get(t, 0) + 1

            for q_token in query_tokens:
                if q_token not in tf_map:
                    continue
                tf = tf_map[q_token]
                idf = self.idf.get(q_token, 0.0)
                denom = tf + self.k1 * (1 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0)))
                score += idf * (tf * (self.k1 + 1)) / (denom or 1.0)

            if score > 0.0:
                scores.append((chunk, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
