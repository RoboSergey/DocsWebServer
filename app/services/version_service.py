from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Version


async def list_versions(
    db: AsyncSession,
    doc_id: str,
) -> list[Version]:
    """Returns all versions for a document (no content), ordered by version_num DESC.

    Returns empty list if document doesn't exist or is deleted.
    """
    doc_stmt = select(Document).where(
        Document.id == doc_id,
        Document.is_deleted.is_(False),
    )
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if doc is None:
        return []

    stmt = (
        select(
            Version.id,
            Version.document_id,
            Version.version_num,
            Version.created_at,
            Version.source,
        )
        .where(Version.document_id == doc_id)
        .order_by(Version.version_num.desc())
    )
    rows = (await db.execute(stmt)).all()

    versions: list[Version] = []
    for row in rows:
        v = Version.__new__(Version)
        v.id = row[0]
        v.document_id = row[1]
        v.version_num = row[2]
        v.created_at = row[3]
        v.source = row[4]
        versions.append(v)

    return versions


async def get_version(
    db: AsyncSession,
    doc_id: str,
    version_num: int,
) -> Version | None:
    """Returns specific version (with content) or None."""
    stmt = select(Version).where(
        Version.document_id == doc_id,
        Version.version_num == version_num,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def restore_version(
    db: AsyncSession,
    doc_id: str,
    version_num: int,
) -> Version | None:
    """Creates a new version with content copied from the specified version.

    source = 'restore'. Returns the new version, or None if document/version not found.
    """
    doc_stmt = select(Document).where(
        Document.id == doc_id,
        Document.is_deleted.is_(False),
    )
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if doc is None:
        return None

    source_version = await get_version(db, doc_id, version_num)
    if source_version is None:
        return None

    content = source_version.content

    for _attempt in range(2):
        max_stmt = select(func.max(Version.version_num)).where(
            Version.document_id == doc_id
        )
        current_max: int | None = (await db.execute(max_stmt)).scalar_one_or_none()
        next_version_num = (current_max or 0) + 1

        new_version = Version(
            document_id=doc_id,
            version_num=next_version_num,
            content=content,
            source="restore",
        )
        db.add(new_version)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        await db.refresh(new_version)
        return new_version

    raise RuntimeError(f"Failed to restore version for document {doc_id} after retries")
