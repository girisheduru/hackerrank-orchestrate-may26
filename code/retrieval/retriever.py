"""BM25-based corpus retriever with per-company filtering."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from rank_bm25 import BM25Okapi

from retrieval.loader import Chunk, CorpusLoader


@dataclass
class SearchResult:
    chunk: Chunk
    score: float


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenizer; strips punctuation."""
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25Retriever:
    """Builds one BM25 index per company and supports filtered search."""

    def __init__(self, corpus: dict[str, list[Chunk]]):
        self._chunks: dict[str, list[Chunk]] = corpus
        self._indexes: dict[str, BM25Okapi] = {}
        for company_key, chunks in corpus.items():
            if chunks:
                tokenized = [_tokenize(c.text) for c in chunks]
                self._indexes[company_key] = BM25Okapi(tokenized)

    @classmethod
    def from_data_dir(cls, data_dir) -> "BM25Retriever":
        from pathlib import Path
        loader = CorpusLoader(Path(data_dir))
        corpus = loader.load()
        return cls(corpus)

    def search(
        self,
        query: str,
        company: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """
        Search BM25 index filtered to `company`.
        company should be one of: hackerrank, claude, visa.
        Returns up to top_k results sorted by score descending.
        """
        key = company.lower()
        if key not in self._indexes:
            # fall back to searching all companies
            return self._search_all(query, top_k, min_score)

        tokenized_query = _tokenize(query)
        scores = self._indexes[key].get_scores(tokenized_query)
        chunks = self._chunks[key]

        ranked = sorted(
            zip(scores, chunks), key=lambda x: x[0], reverse=True
        )[:top_k]

        return [
            SearchResult(chunk=c, score=float(s))
            for s, c in ranked
            if s >= min_score
        ]

    def _search_all(self, query: str, top_k: int, min_score: float) -> list[SearchResult]:
        """Search across all companies and return top-k globally."""
        tokenized_query = _tokenize(query)
        all_results: list[SearchResult] = []
        for key, index in self._indexes.items():
            scores = index.get_scores(tokenized_query)
            for score, chunk in zip(scores, self._chunks[key]):
                if score >= min_score:
                    all_results.append(SearchResult(chunk=chunk, score=float(score)))
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]

    def max_score(self, results: list[SearchResult]) -> float:
        if not results:
            return 0.0
        return max(r.score for r in results)
