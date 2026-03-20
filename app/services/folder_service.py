import uuid

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Folder
from app.schemas import DocumentResponse, FolderTree


async def get_folder(db: AsyncSession, folder_id: str, user_id: str) -> Folder:
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == user_id)
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


async def get_folder_tree(db: AsyncSession, user_id: str) -> list[FolderTree]:
    """Returns top-level folders as a recursive FolderTree list."""
    folders_result = await db.execute(select(Folder).where(Folder.user_id == user_id))
    all_folders = list(folders_result.scalars().all())

    docs_result = await db.execute(
        select(Document).where(Document.user_id == user_id, Document.is_deleted.is_(False))
    )
    all_docs = list(docs_result.scalars().all())

    # Index by id for quick lookup
    folder_map: dict[str, FolderTree] = {}
    for f in all_folders:
        folder_map[f.id] = FolderTree(
            id=f.id,
            name=f.name,
            parent_id=f.parent_id,
            created_at=f.created_at,
            sort_order=f.sort_order,
            children=[],
            documents=[],
        )

    # Attach documents — note: version_count/latest_version default to 0/None
    for doc in all_docs:
        if doc.folder_id and doc.folder_id in folder_map:
            folder_map[doc.folder_id].documents.append(
                DocumentResponse.model_validate(doc)
            )

    # Build tree (attach children to parents, collect roots)
    roots: list[FolderTree] = []
    for ft in folder_map.values():
        if ft.parent_id and ft.parent_id in folder_map:
            folder_map[ft.parent_id].children.append(ft)
        else:
            roots.append(ft)

    for ft in folder_map.values():
        ft.children.sort(key=lambda x: (x.sort_order, x.name))
        ft.documents.sort(key=lambda x: (x.sort_order, x.title))
    roots.sort(key=lambda x: (x.sort_order, x.name))

    return roots


async def create_folder(
    db: AsyncSession, user_id: str, name: str, parent_id: str | None = None
) -> Folder:
    max_stmt = select(func.max(Folder.sort_order)).where(Folder.parent_id == parent_id)
    max_order: int | None = (await db.execute(max_stmt)).scalar_one_or_none()
    sort_order = (max_order if max_order is not None else -1) + 1
    folder = Folder(
        id=str(uuid.uuid4()),
        name=name,
        parent_id=parent_id,
        sort_order=sort_order,
    )
    folder.user_id = user_id
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


async def rename_folder(db: AsyncSession, folder_id: str, user_id: str, name: str) -> Folder | None:
    folder = await get_folder(db, folder_id, user_id)
    folder.name = name
    await db.commit()
    await db.refresh(folder)
    return folder


async def set_folder_position(
    db: AsyncSession, folder_id: str, user_id: str, parent_id: str | None, sort_order: int
) -> tuple[Folder | None, str]:
    """Returns (folder, 'ok') or (None, 'not_found') or (None, 'cycle')."""
    try:
        folder = await get_folder(db, folder_id, user_id)
    except HTTPException:
        return None, "not_found"
    if parent_id is not None:
        # Cycle check: walk ancestors of parent_id to ensure folder_id is not among them
        all_result = await db.execute(select(Folder).where(Folder.user_id == user_id))
        folder_map = {f.id: f for f in all_result.scalars().all()}
        current = parent_id
        while current is not None:
            if current == folder_id:
                return None, "cycle"
            f = folder_map.get(current)
            current = f.parent_id if f else None
    folder.parent_id = parent_id
    folder.sort_order = sort_order
    await db.commit()
    await db.refresh(folder)
    return folder, "ok"


async def delete_folder(db: AsyncSession, folder_id: str, user_id: str) -> bool:
    """Delete folder; re-parent children and documents to the folder's parent."""
    try:
        folder = await get_folder(db, folder_id, user_id)
    except HTTPException:
        return False

    parent_id = folder.parent_id  # could be None (move to root)

    # Re-parent child folders
    await db.execute(
        update(Folder)
        .where(Folder.parent_id == folder_id)
        .values(parent_id=parent_id)
    )

    # Re-parent documents
    await db.execute(
        update(Document)
        .where(Document.folder_id == folder_id)
        .values(folder_id=parent_id)
    )

    await db.delete(folder)
    await db.commit()
    return True
