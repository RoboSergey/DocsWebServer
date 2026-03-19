import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Folder
from app.schemas import DocumentResponse, FolderTree


async def get_folder_tree(db: AsyncSession) -> list[FolderTree]:
    """Returns top-level folders as a recursive FolderTree list."""
    folders_result = await db.execute(select(Folder))
    all_folders = list(folders_result.scalars().all())

    docs_result = await db.execute(
        select(Document).where(Document.is_deleted.is_(False))
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

    return roots


async def create_folder(
    db: AsyncSession, name: str, parent_id: str | None = None
) -> Folder:
    folder = Folder(id=str(uuid.uuid4()), name=name, parent_id=parent_id)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


async def rename_folder(db: AsyncSession, folder_id: str, name: str) -> Folder | None:
    result = await db.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    if folder is None:
        return None
    folder.name = name
    await db.commit()
    await db.refresh(folder)
    return folder


async def delete_folder(db: AsyncSession, folder_id: str) -> bool:
    """Delete folder; re-parent children and documents to the folder's parent."""
    result = await db.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    if folder is None:
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
