from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas import VersionDetail, VersionListResponse, VersionResponse
from app.services import version_service

router = APIRouter(prefix="/api/documents/{doc_id}/versions", tags=["versions"])


@router.get("", response_model=VersionListResponse)
async def list_versions(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> VersionListResponse:
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
) -> VersionDetail:
    version = await version_service.get_version(db, doc_id, version_num)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionDetail.model_validate(version)


@router.post("/{version_num}/restore", response_model=VersionDetail, status_code=201)
async def restore_version(
    doc_id: str,
    version_num: int,
    db: AsyncSession = Depends(get_db),
) -> VersionDetail:
    new_version = await version_service.restore_version(db, doc_id, version_num)
    if new_version is None:
        raise HTTPException(status_code=404, detail="Document or version not found")
    return VersionDetail.model_validate(new_version)
