from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["ui"])

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


@router.get("/", include_in_schema=False)
@router.get("/ui", include_in_schema=False)
def serve_ui() -> FileResponse:
    return FileResponse(INDEX_FILE)
