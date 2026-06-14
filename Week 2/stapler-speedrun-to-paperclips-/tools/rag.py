from __future__ import annotations

import json
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    faiss = None


MODEL_NAME = "all-MiniLM-L6-v2"
ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "rag" / "index" / "faiss.index"
CHUNKS_PATH = ROOT / "rag" / "index" / "chunks.json"
EMBEDDINGS_PATH = ROOT / "rag" / "index" / "embeddings.npy"
EMBEDDING_DIM = 384

@lru_cache(maxsize=1)
def _get_model() -> Any | None:
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(MODEL_NAME)
    except Exception:
        return None


@lru_cache(maxsize=1)
def _get_index() -> faiss.Index:
    if faiss is None:
        raise RuntimeError("FAISS is not installed")
    return faiss.read_index(str(INDEX_PATH))


@lru_cache(maxsize=1)
def _get_chunks() -> tuple[dict[str, Any], ...]:
    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)
    return tuple(data)


@lru_cache(maxsize=1)
def _get_embeddings() -> np.ndarray:
    return np.load(EMBEDDINGS_PATH)


def _fallback_encode(text: str) -> np.ndarray:
    vector = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    tokens = text.lower().split()
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
        vector[index] += 1.0

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector /= norm
    return vector


def query_local_papers(question: str, top_k: int = 5) -> list[dict[str, Any]] | dict[str, str]:
    """Answer questions from locally indexed PDFs using FAISS or NumPy similarity search."""
    if not CHUNKS_PATH.exists() or (faiss is None and not EMBEDDINGS_PATH.exists()) or (
        faiss is not None and not INDEX_PATH.exists() and not EMBEDDINGS_PATH.exists()
    ):
        return {
            "message": (
                "No local RAG index found. Run rag/ingest.py first to build "
                "rag/index/chunks.json and either rag/index/faiss.index or rag/index/embeddings.npy."
            )
        }

    model = _get_model()
    chunks = _get_chunks()

    if model is not None:
        embedding = model.encode([question], normalize_embeddings=True)[0]
    else:
        embedding = _fallback_encode(question)
    query_vector = np.array([embedding], dtype=np.float32)

    if faiss is not None and INDEX_PATH.exists():
        index = _get_index()
        scores, indices = index.search(query_vector, max(1, int(top_k)))
        ranked = list(zip(scores[0], indices[0]))
    else:
        embeddings = _get_embeddings()
        scores = embeddings @ query_vector[0]
        ranked_indices = np.argsort(-scores)[: max(1, int(top_k))]
        ranked = [(float(scores[idx]), int(idx)) for idx in ranked_indices]

    results: list[dict[str, Any]] = []
    for score, idx in ranked:
        if idx < 0 or idx >= len(chunks):
            continue
        chunk = chunks[idx]
        results.append(
            {
                "source": chunk.get("source", ""),
                "page": chunk.get("page", None),
                "relevance": float(score),
                "text": chunk.get("text", ""),
            }
        )

    return results
