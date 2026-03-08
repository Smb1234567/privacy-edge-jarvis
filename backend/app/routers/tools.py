from fastapi import APIRouter

from ..core.tools import list_tools

router = APIRouter(tags=["tools"])


@router.get("/tools")
def tools() -> dict:
    return {"tools": list_tools()}
