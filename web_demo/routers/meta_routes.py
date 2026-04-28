from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..models import DemoMetaResponse
from ..repositories import HTML_FILE
from ..services import get_demo_meta

router = APIRouter()


@router.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/meta", response_model=DemoMetaResponse)
def demo_meta() -> DemoMetaResponse:
    return get_demo_meta()
