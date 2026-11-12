"""Index syllabus chunks and fetch the ones relevant to a topic. Falls back to keyword matching when
no embedding model is available, so generation never depends on it."""

import logging

from app.agents.llm import LLM, LLMError
from app.agents.text import chunk_text, keyword_chunks
from app.agents.vectorstore import VectorStore, collection_name

log = logging.getLogger(__name__)
EMBED_BATCH = 32


def index_syllabus(llm: LLM, store: VectorStore, course_id: str, text: str) -> bool:
    """Embed and store the syllabus. Returns False (and logs) if that is not possible."""
    chunks = chunk_text(text)
    try:
        embeddings: list[list[float]] = []
        for i in range(0, len(chunks), EMBED_BATCH):
            embeddings += llm.embed(chunks[i:i + EMBED_BATCH])
        store.replace(collection_name(course_id), [f"c{i}" for i in range(len(chunks))], chunks, embeddings)
        return True
    except LLMError as e:
        log.warning("retrieval index skipped for %s: %s", course_id, e)
    except Exception:  # noqa: BLE001 - the vector store being down must not fail the job
        log.warning("vector store unavailable for %s", course_id, exc_info=True)
    return False


def retrieve(llm: LLM, store: VectorStore, course_id: str, text: str, query: str, k: int = 4) -> str:
    """Relevant syllabus excerpts for `query`, joined for use in a prompt."""
    try:
        [vec] = llm.embed([query])
        hits = store.query(collection_name(course_id), vec, k)
        if hits:
            return "\n\n---\n\n".join(hits)
    except Exception:  # noqa: BLE001 - fall back to keywords
        pass
    return "\n\n---\n\n".join(keyword_chunks(text, query, k))
