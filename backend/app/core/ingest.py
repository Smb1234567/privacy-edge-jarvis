def ingest_documents(file_names: list[str]) -> dict:
    # Phase 1: wire parsers + chunking + embedding + FAISS persistence.
    return {
        "ingested": len(file_names),
        "files": file_names,
        "status": "stub",
    }
