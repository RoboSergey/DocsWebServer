from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import FolderCreate, FolderPosition, FolderRename, FolderResponse, FolderTree
from app.services import folder_service

router = APIRouter(prefix="/api/folders", tags=["folders"])


@router.get("", response_model=list[FolderTree])
async def list_folders(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[FolderTree]:
    return await folder_service.get_folder_tree(db, user_id=current_user.id)


@router.post("", response_model=FolderResponse, status_code=201)
async def create_folder(
    body: FolderCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> FolderResponse:
    try:
        folder = await folder_service.create_folder(db, user_id=current_user.id, name=body.name, parent_id=body.parent_id)
    except IntegrityError:
        raise HTTPException(status_code=422, detail="Invalid parent_id: folder not found")
    return FolderResponse.model_validate(folder)


@router.put("/{folder_id}", response_model=FolderResponse)
async def rename_folder(
    folder_id: str, body: FolderRename, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> FolderResponse:
    folder = await folder_service.rename_folder(db, folder_id, user_id=current_user.id, name=body.name)
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return FolderResponse.model_validate(folder)


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> None:
    found = await folder_service.delete_folder(db, folder_id, user_id=current_user.id)
    if not found:
        raise HTTPException(status_code=404, detail="Folder not found")


@router.patch("/{folder_id}/position", response_model=FolderResponse)
async def set_folder_position(
    folder_id: str, body: FolderPosition, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> FolderResponse:
    folder, status = await folder_service.set_folder_position(
        db, folder_id, user_id=current_user.id, parent_id=body.parent_id, sort_order=body.sort_order
    )
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Folder not found")
    if status == "cycle":
        raise HTTPException(
            status_code=422,
            detail="Cannot move a folder into its own descendant",
        )
    return FolderResponse.model_validate(folder)
