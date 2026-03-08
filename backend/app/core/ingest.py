from __future__ import annotations

from pathlib import Path

from .rag import BASE_DIR, RAW_DIR, build_index


def ingest_documents(paths: list[str], max_docs: int = 100) -> dict:
    saved = []
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        try:
            rel = path.resolve().relative_to(BASE_DIR)
            saved.append(str(rel))
        except ValueError:
            saved.append(str(path.resolve()))

    index_report = build_index(max_docs=max_docs)
    return {
        "saved_files": saved,
        "indexed": index_report,
        "status": "ok",
    }


def reindex_raw(max_docs: int = 100) -> dict:
    index_report = build_index(max_docs=max_docs)
    return {
        "status": "ok",
        "indexed": index_report,
    }
