import json
import re
from typing import List, Optional, Tuple

import jieba
from rank_bm25 import BM25Okapi

MAX_RAG_CHUNKS = 400
MAX_RAG_TOTAL_CHARS = 180000


class SentenceSplitter:
    def __init__(self, chunk_size: int = 500):
        self.chunk_size = chunk_size

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if self._has_chinese(text):
            return self._split_chinese(text)
        return self._split_english(text)

    @staticmethod
    def _has_chinese(text: str) -> bool:
        return any("\u4e00" <= ch <= "\u9fff" for ch in text)

    def _split_chinese(self, text: str) -> List[str]:
        parts = [p.strip() for p in re.split(r"[\n。！？；…]+", text) if p.strip()]
        return self._merge_parts(parts)

    def _split_english(self, text: str) -> List[str]:
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+", text) if p.strip()]
        return self._merge_parts(parts)

    def _merge_parts(self, parts: List[str]) -> List[str]:
        chunks = []
        current = ""
        for p in parts:
            if len(current) + len(p) + 1 <= self.chunk_size:
                current = f"{current} {p}".strip()
            else:
                if current:
                    chunks.append(current)
                current = p
        if current:
            chunks.append(current)
        return chunks


class RAGRetriever:
    def __init__(self, chunks: List[str]):
        self.chunks = [c for c in chunks if c and c.strip()]
        self._tokenized = [self._tokenize(c) for c in self.chunks]
        self._bm25 = BM25Okapi(self._tokenized) if self._tokenized else None

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        if any("\u4e00" <= ch <= "\u9fff" for ch in text):
            return [t.strip() for t in jieba.cut(text) if t.strip()]
        return re.findall(r"[a-zA-Z0-9_]+", text.lower())

    def search(self, query: str, top_k: int = 3) -> List[str]:
        ranked = self.search_with_scores(query, top_k)
        return [t for t, _ in ranked]

    def search_with_scores(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """返回 (片段文本, BM25 分数)，分数越高越相关。思路对齐多文档 RAG 中的 top-k 检索。"""
        if not query or not self._bm25:
            return []
        q_tokens = self._tokenize(query)
        scores = self._bm25.get_scores(q_tokens)
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        positive = [(self.chunks[i], float(scores[i])) for i in top_idx if scores[i] > 0]
        if positive:
            return positive
        return [(self.chunks[i], float(scores[i])) for i in top_idx]


def build_rag_chunks(content_list: List[str], chunk_size: int = 500) -> List[str]:
    full_text = "\n".join([c.strip() for c in content_list if c and c.strip()])
    splitter = SentenceSplitter(chunk_size=chunk_size)
    return splitter.split_text(full_text)


def _trim_rag_chunks(chunks: List[str]) -> List[str]:
    if not chunks:
        return []

    trimmed = []
    total = 0
    for c in chunks:
        c = (c or "").strip()
        if not c:
            continue
        if len(trimmed) >= MAX_RAG_CHUNKS:
            break
        if total + len(c) > MAX_RAG_TOTAL_CHARS:
            break
        trimmed.append(c)
        total += len(c)
    return trimmed


def dumps_rag_chunks(chunks: List[str]) -> str:
    safe_chunks = _trim_rag_chunks(chunks or [])
    return json.dumps(safe_chunks, ensure_ascii=False)


def loads_rag_chunks(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if isinstance(data, list):
        return [str(x) for x in data if x]
    return []


def get_rag_context(question: str, rag_chunks: List[str], top_k: int = 3) -> str:
    retriever = RAGRetriever(rag_chunks)
    hits = retriever.search(question, top_k=top_k)
    if not hits:
        return ""
    return "\n\n".join([f"[片段{i + 1}] {c}" for i, c in enumerate(hits)])
