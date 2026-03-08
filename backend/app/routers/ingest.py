from fastapi import APIRouter, UploadFile

from ..core.ingest import ingest_documents

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
async def ingest(files: list[UploadFile]) -> dict:
    file_names = [f.filename for f in files]
    return ingest_documents(file_names)
