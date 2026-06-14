from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import numpy as np

import fitz

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    faiss = None


MODEL_NAME = "all-MiniLM-L6-v2"
ROOT = Path(__file__).resolve().parent.parent
PAPERS_DIR = ROOT / "rag" / "papers"
INDEX_DIR = ROOT / "rag" / "index"
INDEX_PATH = INDEX_DIR / "faiss.index"
CHUNKS_PATH = INDEX_DIR / "chunks.json"
EMBEDDINGS_PATH = INDEX_DIR / "embeddings.npy"
EMBEDDING_DIM = 384


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    step = max(1, chunk_size - overlap)

    while start < len(cleaned):
        end = start + chunk_size
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


def extract_pdf_chunks(pdf_path: Path) -> list[dict[str, Any]]:
    doc = fitz.open(pdf_path)
    items: list[dict[str, Any]] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text("text")
        for chunk in chunk_text(text):
            items.append(
                {
                    "text": chunk,
                    "source": pdf_path.name,
                    "page": page_idx + 1,
                }
            )

    doc.close()
    return items


def encode_texts(texts: list[str]) -> np.ndarray:
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
        embeddings = model.encode(texts, normalize_embeddings=True)
        return np.asarray(embeddings, dtype=np.float32)
    except Exception:
        embeddings = np.zeros((len(texts), EMBEDDING_DIM), dtype=np.float32)
        for row_index, text in enumerate(texts):
            tokens = text.lower().split()
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
                embeddings[row_index, index] += 1.0

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embeddings /= norms
        return embeddings


def main() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))
    if not pdf_files:
        print("No PDFs found in rag/papers/. Add files and rerun.")
        return

    all_chunks: list[dict[str, Any]] = []
    for pdf in pdf_files:
        all_chunks.extend(extract_pdf_chunks(pdf))

    if not all_chunks:
        print("No text chunks extracted from PDFs.")
        return

    texts = [item["text"] for item in all_chunks]

    embeddings = encode_texts(texts)

    with CHUNKS_PATH.open("w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=True, indent=2)

    np.save(EMBEDDINGS_PATH, embeddings)

    if faiss is not None:
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(INDEX_PATH))

    print(f"Indexed {len(all_chunks)} chunks from {len(pdf_files)} PDFs")
    if faiss is not None:
        print(f"Saved FAISS index to {INDEX_PATH}")
    print(f"Saved embedding matrix to {EMBEDDINGS_PATH}")
    print(f"Saved chunk metadata to {CHUNKS_PATH}")


if __name__ == "__main__":
    main()
