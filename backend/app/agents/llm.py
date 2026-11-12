"""Model access. One interface, two providers: Ollama (real) and a deterministic fake (tests/CI).

Every structured call is validated against a Pydantic model. If the model returns invalid JSON or
the wrong shape, it is shown its error once and asked to correct it; after that we give up and let
the job record the failure instead of storing guesses.
"""

import base64
import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """The model could not produce a usable answer (network, timeout, or invalid output)."""


class EmbeddingUnavailable(LLMError):
    """No embedding model is installed/reachable. Callers fall back to no retrieval."""


class LLM(ABC):
    last_usage: dict = {}

    def _trace(self, schema: str, attempt: int, started: float, outcome: str) -> None:
        """One log line per model call: what it was for, how long it took, tokens in and out."""
        ms = round((time.perf_counter() - started) * 1000)
        info = {"schema": schema, "attempt": attempt + 1, "outcome": outcome, "ms": ms, **self.last_usage}
        log.info("llm call %s %s in %dms", schema, outcome, ms, extra={"llm": info})

    @abstractmethod
    def _chat(self, messages: list[dict], schema: dict | None, think: str, temperature: float) -> str: ...

    @abstractmethod
    def ocr(self, image_png: bytes) -> str:
        """Transcribe a page image (printed or handwritten) to plain text."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def health(self) -> dict: ...

    def structured(self, system: str, user: str, schema: type[T], *, think: str = "low",
                   temperature: float = 0.2) -> T:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        json_schema = schema.model_json_schema()
        last_error = ""
        for attempt in range(2):  # the original try plus one repair
            started = time.perf_counter()
            self.last_usage = {}
            try:
                raw = self._chat(messages, json_schema, think, temperature)
            except LLMError:
                self._trace(schema.__name__, attempt, started, "unreachable")
                raise
            try:
                out = schema.model_validate(json.loads(raw))
                self._trace(schema.__name__, attempt, started, "ok")
                return out
            except (json.JSONDecodeError, ValidationError) as e:
                self._trace(schema.__name__, attempt, started, "invalid")
                last_error = str(e)[:600]
                log.warning("invalid model output (attempt %d): %s", attempt + 1, last_error)
                messages = [
                    *messages,
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": "That JSON was invalid: "
                     f"{last_error}\nReturn only corrected JSON that matches the schema."},
                ]
        raise LLMError(f"The model returned invalid output twice: {last_error}")


class OllamaLLM(LLM):
    def __init__(self) -> None:
        s = get_settings()
        self.s = s
        self.http = httpx.Client(
            base_url=s.ollama_url.rstrip("/"),
            timeout=httpx.Timeout(s.llm_timeout_seconds, connect=10),
        )

    def _post(self, path: str, body: dict) -> dict:
        last: Exception | None = None
        for attempt in range(self.s.llm_retries + 1):
            try:
                r = self.http.post(path, json=body)
                if r.status_code >= 500:
                    raise httpx.HTTPStatusError(r.text[:200], request=r.request, response=r)
                if r.status_code >= 400:
                    raise LLMError(f"Ollama rejected the request ({r.status_code}): {r.text[:300]}")
                return r.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last = e
                log.warning("ollama %s failed (attempt %d): %s", path, attempt + 1, e)
                time.sleep(min(2 ** attempt, 8))
        raise LLMError(f"Could not reach the model server: {last}")

    def _chat(self, messages, schema, think, temperature) -> str:
        body: dict[str, Any] = {
            "model": self.s.llm_model, "messages": messages, "stream": False, "think": think,
            "options": {"temperature": temperature, "num_ctx": self.s.llm_num_ctx},
        }
        if schema:
            body["format"] = schema
        res = self._post("/api/chat", body)
        self.last_usage = {"prompt_tokens": res.get("prompt_eval_count"), "output_tokens": res.get("eval_count")}
        return res["message"]["content"]

    def ocr(self, image_png: bytes) -> str:
        body = {
            "model": self.s.vision_model, "stream": False, "think": False,
            "options": {"temperature": 0, "num_ctx": self.s.llm_num_ctx},
            "messages": [{
                "role": "user",
                "content": (
                    "Transcribe all the text on this page exactly as written, in reading order. "
                    "Keep headings, numbering and bullet points. Do not summarise, translate or add "
                    "commentary. If a word is unreadable write [illegible]. Output only the text."
                ),
                "images": [base64.b64encode(image_png).decode()],
            }],
        }
        return self._post("/api/chat", body)["message"]["content"].strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            r = self.http.post("/api/embed", json={"model": self.s.embed_model, "input": texts})
        except httpx.TransportError as e:
            raise LLMError(f"Could not reach the model server: {e}") from e
        if r.status_code == 404:
            raise EmbeddingUnavailable(f"Embedding model '{self.s.embed_model}' is not installed")
        if r.status_code >= 400:
            raise LLMError(f"Embedding request failed ({r.status_code}): {r.text[:200]}")
        return r.json()["embeddings"]

    def health(self) -> dict:
        try:
            names = {m["name"] for m in self.http.get("/api/tags", timeout=10).json()["models"]}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)[:200]}

        def has(name: str) -> bool:
            return name in names or f"{name}:latest" in names

        return {
            "ok": has(self.s.llm_model), "provider": "ollama", "url": self.s.ollama_url,
            "text_model": {"name": self.s.llm_model, "available": has(self.s.llm_model)},
            "vision_model": {"name": self.s.vision_model, "available": has(self.s.vision_model)},
            "embed_model": {"name": self.s.embed_model, "available": has(self.s.embed_model)},
        }


class FakeLLM(LLM):
    """Deterministic stand-in. `responder(messages, schema_title)` returns a dict (or raw text)."""

    def __init__(self, responder: Callable[[list[dict], str], Any] | None = None, *, embeddings: bool = True):
        from app.agents.fake_responder import default_responder

        self.responder = responder or default_responder
        self.calls: list[dict] = []
        self.ocr_texts: list[str] = []
        self.embeddings = embeddings

    def _chat(self, messages, schema, think, temperature) -> str:
        title = (schema or {}).get("title", "")
        self.calls.append({"schema": title, "messages": messages})
        out = self.responder(messages, title)
        return out if isinstance(out, str) else json.dumps(out)

    def ocr(self, image_png: bytes) -> str:
        self.calls.append({"schema": "ocr", "bytes": len(image_png)})
        return self.ocr_texts.pop(0) if self.ocr_texts else "1. Scanned topic\n- a point"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.embeddings:
            raise EmbeddingUnavailable("no embedding model")
        return [_hash_embed(t) for t in texts]

    def health(self) -> dict:
        return {"ok": True, "provider": "fake"}


def _hash_embed(text: str, dims: int = 64) -> list[float]:
    """Bag-of-words hashing embedding: texts sharing words are close. Good enough for tests."""
    import hashlib
    import math

    v = [0.0] * dims
    for w in text.lower().split():
        h = int(hashlib.md5(w.strip(".,;:()").encode()).hexdigest(), 16)  # noqa: S324 - not security
        v[h % dims] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


_override: LLM | None = None


def set_llm(llm: LLM | None) -> None:
    """Swap the provider (tests)."""
    global _override
    _override = llm


def get_llm() -> LLM:
    if _override is not None:
        return _override
    return FakeLLM() if get_settings().llm_provider == "fake" else OllamaLLM()
