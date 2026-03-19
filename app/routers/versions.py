from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import VersionDetail, VersionListResponse, VersionResponse
from app.services import version_service
from app.services.document_service import get_document

router = APIRouter(prefix="/api/documents/{doc_id}/versions", tags=["versions"])


@router.get("", response_model=VersionListResponse)
async def list_versions(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VersionListResponse:
    if await get_document(db, doc_id, user_id=current_user.id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    versions = await version_service.list_versions(db, doc_id)
    return VersionListResponse(
        versions=[VersionResponse.model_validate(v) for v in versions],
        total=len(versions),
    )


@router.get("/{version_num}", response_model=VersionDetail)
async def get_version(
    doc_id: str,
    version_num: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VersionDetail:
    if await get_document(db, doc_id, user_id=current_user.id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    version = await version_service.get_version(db, doc_id, version_num)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionDetail.model_validate(version)


@router.post("/{version_num}/restore", response_model=VersionDetail, status_code=201)
async def restore_version(
    doc_id: str,
    version_num: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VersionDetail:
    if await get_document(db, doc_id, user_id=current_user.id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    new_version = await version_service.restore_version(db, doc_id, version_num)
    if new_version is None:
        raise HTTPException(status_code=404, detail="Document or version not found")
    return VersionDetail.model_validate(new_version)
