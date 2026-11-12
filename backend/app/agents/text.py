"""Plain-text helpers: chunking and a keyword retriever used when embeddings are unavailable."""

import re

CHUNK_CHARS = 1200
OVERLAP = 150


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Split on paragraph boundaries into chunks of about `size` characters."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        while len(p) > size:  # one huge paragraph: cut it
            chunks.append(p[:size])
            p = p[size - overlap:]
        if cur and len(cur) + len(p) + 2 > size:
            chunks.append(cur)
            cur = cur[-overlap:] + "\n\n" + p if overlap else p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks


_STOP = {"the", "and", "of", "to", "in", "a", "an", "for", "with", "on", "is", "are", "as", "by", "or"}


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9+#]+", s.lower()) if len(w) > 2 and w not in _STOP}


def keyword_chunks(text: str, query: str, k: int = 4) -> list[str]:
    """Top-k chunks by word overlap with the query. Deterministic, no model needed."""
    q = _words(query)
    chunks = chunk_text(text)
    scored = sorted(enumerate(chunks), key=lambda ic: (-len(q & _words(ic[1])), ic[0]))
    best = [c for _, c in scored[:k]]
    return best or chunks[:k]
