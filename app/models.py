import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    share_mode: Mapped[str] = mapped_column(String, default="public")
    share_token: Mapped[str | None] = mapped_column(String, nullable=True)

    versions: Mapped[list["Version"]] = relationship(
        "Version", back_populates="document", cascade="all, delete-orphan"
    )


class Version(Base):
    __tablename__ = "versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    source: Mapped[str] = mapped_column(String, default="editor")

    document: Mapped["Document"] = relationship("Document", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("document_id", "version_num", name="uq_document_version"),
        Index("ix_versions_document_version_desc", "document_id", "version_num"),
    )
