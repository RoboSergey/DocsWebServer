import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import ShareSettings, ShareUpdate
from app.services import document_service

router = APIRouter(prefix="/api/documents", tags=["sharing"])


def _build_share_url(request: Request, doc_id: str, share_token: str | None, share_mode: str) -> str | None:
    base = str(request.base_url).rstrip("/")
    if share_mode == "token" and share_token:
        return f"{base}/preview/{doc_id}?token={share_token}"
    return f"{base}/preview/{doc_id}"


@router.get("/{doc_id}/sharing", response_model=ShareSettings)
async def get_share_settings(
    doc_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShareSettings:
    doc = await document_service.get_document(db, doc_id, user_id=current_user.id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    share_url = _build_share_url(request, doc_id, doc.share_token, doc.share_mode)
    return ShareSettings(
        share_mode=doc.share_mode,
        share_token=doc.share_token,
        share_url=share_url,
    )


@router.put("/{doc_id}/sharing", response_model=ShareSettings)
async def update_share_settings(
    doc_id: str,
    body: ShareUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShareSettings:
    doc = await document_service.get_document(db, doc_id, user_id=current_user.id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.share_mode = body.share_mode
    if body.share_mode == "token" and doc.share_token is None:
        doc.share_token = secrets.token_urlsafe(32)
    # If setting to 'public', keep existing token (don't clear it)

    await db.commit()
    await db.refresh(doc)

    share_url = _build_share_url(request, doc_id, doc.share_token, doc.share_mode)
    return ShareSettings(
        share_mode=doc.share_mode,
        share_token=doc.share_token,
        share_url=share_url,
    )


@router.post("/{doc_id}/sharing/regenerate-token", response_model=ShareSettings)
async def regenerate_share_token(
    doc_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShareSettings:
    doc = await document_service.get_document(db, doc_id, user_id=current_user.id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.share_token = secrets.token_urlsafe(32)

    await db.commit()
    await db.refresh(doc)

    share_url = _build_share_url(request, doc_id, doc.share_token, doc.share_mode)
    return ShareSettings(
        share_mode=doc.share_mode,
        share_token=doc.share_token,
        share_url=share_url,
    )
