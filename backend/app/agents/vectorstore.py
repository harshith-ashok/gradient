"""Vector store for syllabus chunks (retrieval for grounded generation).

ChromaDB in production, an in-process store when CHROMA_URL is unset (dev/tests). Embeddings are
computed by us (through Ollama) and passed in, so Chroma never downloads an embedding model.
"""

import math
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from app.core.config import get_settings


class VectorStore(ABC):
    @abstractmethod
    def replace(self, collection: str, ids: list[str], docs: list[str], embeddings: list[list[float]]) -> None:
        """Replace the whole collection's contents."""

    @abstractmethod
    def query(self, collection: str, embedding: list[float], k: int) -> list[str]: ...

    @abstractmethod
    def delete(self, collection: str) -> None: ...


class MemoryStore(VectorStore):
    def __init__(self) -> None:
        self.data: dict[str, list[tuple[str, list[float]]]] = {}

    def replace(self, collection, ids, docs, embeddings):
        self.data[collection] = list(zip(docs, embeddings, strict=True))

    def query(self, collection, embedding, k):
        def cos(a, b):
            na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
            return sum(x * y for x, y in zip(a, b, strict=False)) / ((na * nb) or 1)

        ranked = sorted(self.data.get(collection, []), key=lambda d: cos(embedding, d[1]), reverse=True)
        return [doc for doc, _ in ranked[:k]]

    def delete(self, collection):
        self.data.pop(collection, None)


class ChromaStore(VectorStore):
    def __init__(self, url: str) -> None:
        import chromadb

        u = urlparse(url)
        self.client = chromadb.HttpClient(host=u.hostname, port=u.port or 8000)

    def replace(self, collection, ids, docs, embeddings):
        self.delete(collection)
        col = self.client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})
        col.add(ids=ids, documents=docs, embeddings=embeddings)

    def query(self, collection, embedding, k):
        col = self.client.get_collection(collection)
        res = col.query(query_embeddings=[embedding], n_results=k)
        return list(res["documents"][0])

    def delete(self, collection):
        try:
            self.client.delete_collection(collection)
        except Exception:  # noqa: BLE001 - nothing to delete
            pass


_store: VectorStore | None = None


def set_store(store: VectorStore | None) -> None:
    global _store
    _store = store


def get_store() -> VectorStore:
    global _store
    if _store is None:
        url = get_settings().chroma_url
        _store = ChromaStore(url) if url else MemoryStore()
    return _store


def collection_name(course_id: str) -> str:
    return f"syllabus_{course_id}".replace("-", "_")[:60]
