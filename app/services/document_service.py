import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Version


async def list_documents(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Document], int]:
    """Returns (documents, total_count), excluding soft-deleted documents.

    Each Document instance is augmented with .version_count and .latest_version
    attributes so that the response schemas can populate those fields.
    """
    version_counts = (
        select(
            Version.document_id,
            func.count(Version.id).label("version_count"),
            func.max(Version.version_num).label("latest_version"),
        )
        .group_by(Version.document_id)
        .subquery()
    )

    # Total count query
    count_stmt = (
        select(func.count(Document.id))
        .where(Document.is_deleted.is_(False))
    )
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Paginated query with version stats
    stmt = (
        select(
            Document,
            func.coalesce(version_counts.c.version_count, 0).label("version_count"),
            version_counts.c.latest_version,
        )
        .outerjoin(version_counts, Document.id == version_counts.c.document_id)
        .where(Document.is_deleted.is_(False))
        .order_by(Document.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    rows = (await db.execute(stmt)).all()

    documents: list[Document] = []
    for row in rows:
        doc: Document = row[0]
        doc.version_count = row[1]  # type: ignore[attr-defined]
        doc.latest_version = row[2]  # type: ignore[attr-defined]
        documents.append(doc)

    return documents, total


async def get_document(db: AsyncSession, doc_id: str) -> Document | None:
    """Returns Document or None if not found / soft-deleted."""
    stmt = select(Document).where(
        Document.id == doc_id,
        Document.is_deleted.is_(False),
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_document(
    db: AsyncSession,
    title: str,
    content: str = "",
) -> Document:
    """Creates a Document, optionally creating the first Version."""
    doc = Document(
        id=str(uuid.uuid4()),
        title=title,
    )
    db.add(doc)
    await db.flush()  # generate the PK before creating Version

    if content:
        version = Version(
            document_id=doc.id,
            version_num=1,
            content=content,
            source="editor",
        )
        db.add(version)

    await db.commit()
    await db.refresh(doc)
    return doc


async def update_document_title(
    db: AsyncSession,
    doc_id: str,
    title: str,
) -> Document | None:
    """Updates document title. Returns updated Document or None if not found."""
    doc = await get_document(db, doc_id)
    if doc is None:
        return None

    doc.title = title
    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def delete_document(db: AsyncSession, doc_id: str) -> bool:
    """Soft-deletes a document. Returns True if found, False otherwise."""
    doc = await get_document(db, doc_id)
    if doc is None:
        return False

    doc.is_deleted = True
    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return True


async def save_content(
    db: AsyncSession,
    doc_id: str,
    content: str,
    source: str = "editor",
) -> Version | None:
    """Creates a new Version for the document. Returns new Version or None if not found."""
    doc = await get_document(db, doc_id)
    if doc is None:
        return None

    for _attempt in range(2):
        # Determine next version_num
        max_stmt = select(func.max(Version.version_num)).where(
            Version.document_id == doc_id
        )
        current_max: int | None = (await db.execute(max_stmt)).scalar_one_or_none()
        next_version_num = (current_max or 0) + 1

        version = Version(
            document_id=doc_id,
            version_num=next_version_num,
            content=content,
            source=source,
        )
        db.add(version)

        doc.updated_at = datetime.now(timezone.utc)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        await db.refresh(version)
        return version

    # Both attempts failed — re-raise
    raise RuntimeError(f"Failed to save version for document {doc_id} after retries")


async def upload_content(
    db: AsyncSession,
    doc_id: str,
    content: str,
) -> Version | None:
    """Same as save_content but source='upload'."""
    return await save_content(db, doc_id, content, source="upload")


async def get_latest_content(db: AsyncSession, doc_id: str) -> str | None:
    """Returns content of latest version (by version_num DESC) or None."""
    stmt = (
        select(Version.content)
        .where(Version.document_id == doc_id)
        .order_by(Version.version_num.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()
