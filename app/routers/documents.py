from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Document, Version
from app.schemas import (
    ContentSave,
    DocumentCreate,
    DocumentDetail,
    DocumentListResponse,
    DocumentMove,
    DocumentPosition,
    DocumentResponse,
    DocumentUpdate,
)
from app.services import document_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


async def _attach_version_stats(db: AsyncSession, doc: Document) -> None:
    """Attach version_count and latest_version onto a Document instance in-place."""
    stats_stmt = select(
        func.count(Version.id).label("version_count"),
        func.max(Version.version_num).label("latest_version"),
    ).where(Version.document_id == doc.id)
    row = (await db.execute(stats_stmt)).one()
    doc.version_count = row[0] or 0  # type: ignore[attr-defined]
    doc.latest_version = row[1]  # type: ignore[attr-defined]


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    folder_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    documents, total = await document_service.list_documents(
        db, page=page, page_size=page_size, folder_id=folder_id
    )
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=DocumentDetail, status_code=201)
async def create_document(
    body: DocumentCreate,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    doc = await document_service.create_document(db, title=body.title, content=body.content, folder_id=body.folder_id)
    await _attach_version_stats(db, doc)
    content = await document_service.get_latest_content(db, doc.id)
    result = DocumentDetail.model_validate(doc)
    result.content = content
    return result


@router.get("/{doc_id}", response_model=DocumentDetail)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    doc = await document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    await _attach_version_stats(db, doc)
    content = await document_service.get_latest_content(db, doc_id)

    result = DocumentDetail.model_validate(doc)
    result.content = content
    return result


@router.put("/{doc_id}", response_model=DocumentDetail)
async def update_document(
    doc_id: str,
    body: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    doc = await document_service.update_document_title(db, doc_id, body.title)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    await _attach_version_stats(db, doc)
    content = await document_service.get_latest_content(db, doc_id)

    result = DocumentDetail.model_validate(doc)
    result.content = content
    return result


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    found = await document_service.delete_document(db, doc_id)
    if not found:
        raise HTTPException(status_code=404, detail="Document not found")


@router.put("/{doc_id}/content", response_model=DocumentDetail)
async def save_content(
    doc_id: str,
    body: ContentSave,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    version = await document_service.save_content(
        db, doc_id, body.content, source=body.source
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = await document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await _attach_version_stats(db, doc)

    result = DocumentDetail.model_validate(doc)
    result.content = body.content
    return result


@router.put("/{doc_id}/move", response_model=DocumentDetail)
async def move_document(
    doc_id: str,
    body: DocumentMove,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    try:
        doc = await document_service.move_document(db, doc_id, body.folder_id)
    except IntegrityError:
        raise HTTPException(status_code=422, detail="Invalid folder_id: folder not found")
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await _attach_version_stats(db, doc)
    content = await document_service.get_latest_content(db, doc_id)
    result = DocumentDetail.model_validate(doc)
    result.content = content
    return result


@router.patch("/{doc_id}/position", response_model=DocumentResponse)
async def set_document_position(
    doc_id: str, body: DocumentPosition, db: AsyncSession = Depends(get_db)
) -> DocumentResponse:
    doc = await document_service.set_document_position(
        db, doc_id, body.folder_id, body.sort_order
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.version_count = 0   # type: ignore[attr-defined]
    doc.latest_version = None   # type: ignore[attr-defined]
    return DocumentResponse.model_validate(doc)


@router.post("/{doc_id}/upload", response_model=DocumentDetail)
async def upload_content(
    doc_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    if file.content_type and not file.content_type.startswith(("text/", "application/xhtml")):
        raise HTTPException(status_code=400, detail="Only HTML files are accepted")

    MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="File is not valid UTF-8")

    version = await document_service.upload_content(db, doc_id, content)
    if version is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = await document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await _attach_version_stats(db, doc)

    result = DocumentDetail.model_validate(doc)
    result.content = content
    return result
