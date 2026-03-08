from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz
from docx import Document

BASE_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = BASE_DIR / "data" / "raw"
INDEX_DIR = BASE_DIR / "data" / "index"
CHUNKS_PATH = INDEX_DIR / "chunks.json"

EMBED_DIMS = 384


@dataclass
class Chunk:
    chunk_id: str
    source: str
    text: str


def _ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _read_pdf(path: Path) -> str:
    doc = fitz.open(path)
    text = "\n".join(page.get_text("text") for page in doc)
    doc.close()
    return text


def _read_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _clean_text(_read_pdf(path))
    if suffix == ".docx":
        return _clean_text(_read_docx(path))
    if suffix in {".txt", ".md", ".markdown", ".rst", ".json", ".csv"}:
        return _clean_text(_read_text(path))
    # Fallback for unknown text-like files.
    return _clean_text(_read_text(path))


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def _hash_embedding(text: str, dims: int = EMBED_DIMS) -> list[float]:
    vec = [0.0] * dims
    for token in _tokenize(text):
        idx = hash(token) % dims
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _cosine(a: list[float], b: list[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def _iter_raw_docs() -> Iterable[Path]:
    allowed = {
        ".pdf",
        ".txt",
        ".md",
        ".markdown",
        ".rst",
        ".docx",
        ".json",
        ".csv",
    }
    for p in RAW_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() in allowed:
            yield p


def save_chunks(chunks: list[dict]) -> None:
    _ensure_dirs()
    CHUNKS_PATH.write_text(json.dumps(chunks, ensure_ascii=True, indent=2), encoding="utf-8")


def load_chunks() -> list[dict]:
    _ensure_dirs()
    if not CHUNKS_PATH.exists():
        return []
    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def index_status() -> dict:
    chunks = load_chunks()
    sources = sorted({c.get("source", "unknown") for c in chunks})
    return {
        "chunks": len(chunks),
        "documents": len(sources),
        "sources_preview": sources[:10],
        "index_file": str(CHUNKS_PATH.relative_to(BASE_DIR)),
    }


def build_index(max_docs: int = 100) -> dict:
    docs = list(_iter_raw_docs())[:max_docs]
    all_chunks: list[dict] = []

    for path in docs:
        try:
            text = read_document(path)
        except Exception as exc:  # noqa: BLE001
            all_chunks.append(
                {
                    "chunk_id": f"{path.name}::error",
                    "source": str(path.relative_to(BASE_DIR)),
                    "text": f"[parse_error] {exc}",
                    "embedding": _hash_embedding(str(path)),
                }
            )
            continue

        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append(
                {
                    "chunk_id": f"{path.name}::{i}",
                    "source": str(path.relative_to(BASE_DIR)),
                    "text": chunk,
                    "embedding": _hash_embedding(chunk),
                }
            )

    save_chunks(all_chunks)
    return {
        "documents_indexed": len(docs),
        "chunks_indexed": len(all_chunks),
        "index_file": str(CHUNKS_PATH.relative_to(BASE_DIR)),
    }


def retrieve(query: str, top_k: int = 4) -> list[dict]:
    chunks = load_chunks()
    if not chunks:
        return []

    q_emb = _hash_embedding(query)
    ranked = []
    for c in chunks:
        emb = c.get("embedding")
        if not emb:
            emb = _hash_embedding(c.get("text", ""))
        ranked.append((c, _cosine(q_emb, emb)))

    ranked.sort(key=lambda x: x[1], reverse=True)
    top = ranked[: max(top_k, 1)]
    return [
        {
            "chunk_id": item["chunk_id"],
            "source": item["source"],
            "text": item["text"],
            "score": round(score, 4),
        }
        for item, score in top
    ]


def search_local(query: str, top_k: int = 3) -> list[dict]:
    return retrieve(query=query, top_k=top_k)
