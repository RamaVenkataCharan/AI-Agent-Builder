import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional
from app.memory.base import BaseMemory, MemoryRecord


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def _cosine_similarity(vec1: Counter, vec2: Counter) -> float:
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x] ** 2 for x in vec1.keys()])
    sum2 = sum([vec2[x] ** 2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    return float(numerator) / denominator


class InMemoryVectorStore(BaseMemory):
    """
    Lightweight, self-contained Vector Store using Term Frequency Cosine Similarity.
    Requires no external native dependencies or server setups.
    """

    def __init__(self):
        self._records: Dict[str, MemoryRecord] = {}
        self._vectors: Dict[str, Counter] = {}

    def add(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        record = MemoryRecord(
            id=doc_id,
            content=content,
            metadata=metadata or {},
        )
        self._records[doc_id] = record
        tokens = _tokenize(content)
        self._vectors[doc_id] = Counter(tokens)

    def search(self, query: str, top_k: int = 3) -> List[MemoryRecord]:
        if not self._records:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return list(self._records.values())[:top_k]

        query_vec = Counter(query_tokens)
        scored: List[MemoryRecord] = []

        for doc_id, record in self._records.items():
            doc_vec = self._vectors.get(doc_id, Counter())
            score = _cosine_similarity(query_vec, doc_vec)
            # Make a copy with score attached
            rec_with_score = MemoryRecord(
                id=record.id,
                content=record.content,
                metadata=record.metadata,
                score=score,
            )
            scored.append(rec_with_score)

        # Sort descending by score
        scored.sort(key=lambda r: r.score or 0.0, reverse=True)
        return scored[:top_k]

    def get_all(self) -> List[MemoryRecord]:
        return list(self._records.values())

    def clear(self) -> None:
        self._records.clear()
        self._vectors.clear()
