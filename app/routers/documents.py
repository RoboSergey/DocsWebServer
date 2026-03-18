from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Document, Version
from app.schemas import (
    ContentSave,
    DocumentCreate,
    DocumentDetail,
    DocumentListResponse,
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
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    documents, total = await document_service.list_documents(db, page=page, page_size=page_size)
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
    doc = await document_service.create_document(db, title=body.title, content=body.content)
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
    await _attach_version_stats(db, doc)

    result = DocumentDetail.model_validate(doc)
    result.content = body.content
    return result


@router.post("/{doc_id}/upload", response_model=DocumentDetail)
async def upload_content(
    doc_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    raw = await file.read()
    content = raw.decode("utf-8")

    version = await document_service.upload_content(db, doc_id, content)
    if version is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = await document_service.get_document(db, doc_id)
    await _attach_version_stats(db, doc)

    result = DocumentDetail.model_validate(doc)
    result.content = content
    return result
