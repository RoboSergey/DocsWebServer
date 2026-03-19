import secrets
import socket

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services import document_service
from app.templates_config import templates

router = APIRouter(tags=["pages"])


@router.get("/api/server-info")
async def server_info(request: Request):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = request.base_url.hostname
    port = request.base_url.port
    scheme = request.base_url.scheme
    origin = f"{scheme}://{local_ip}" + (f":{port}" if port and port not in (80, 443) else "")
    return JSONResponse({"origin": origin})


@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def _check_token(doc_share_mode: str, doc_share_token: str | None, provided_token: str | None) -> None:
    """Raise 403 if share_mode is 'token' and provided token does not match."""
    if doc_share_mode == "token":
        if provided_token is None or doc_share_token is None:
            raise HTTPException(status_code=403, detail="Invalid or missing share token")
        if not secrets.compare_digest(provided_token, doc_share_token):
            raise HTTPException(status_code=403, detail="Invalid or missing share token")


@router.get("/preview/{doc_id}")
async def preview_document(
    doc_id: str,
    request: Request,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    doc = await document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    _check_token(doc.share_mode, doc.share_token, token)

    content = await document_service.get_latest_content(db, doc_id)
    return templates.TemplateResponse(
        "preview.html",
        {"request": request, "document": doc, "content": content},
    )


@router.get("/preview/{doc_id}/raw")
async def preview_document_raw(
    doc_id: str,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    doc = await document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    _check_token(doc.share_mode, doc.share_token, token)

    content = await document_service.get_latest_content(db, doc_id)
    return Response(content=content or "", media_type="text/html")
