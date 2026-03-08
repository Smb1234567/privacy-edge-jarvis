from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from ..core.ingest import reindex_raw
from ..core.rag import RAW_DIR

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
async def ingest(files: list[UploadFile] = File(...)) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    written = []

    for f in files:
        if not f.filename:
            continue
        dest = RAW_DIR / Path(f.filename).name
        data = await f.read()
        dest.write_bytes(data)
        written.append(str(dest))

    report = reindex_raw(max_docs=100)
    report["uploaded_files"] = [Path(p).name for p in written]
    return report


@router.post("/ingest/reindex")
def reindex() -> dict:
    return reindex_raw(max_docs=100)
