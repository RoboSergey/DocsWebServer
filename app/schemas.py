from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Request schemas
class DocumentCreate(BaseModel):
    title: str
    content: str = ""  # optional initial content


class DocumentUpdate(BaseModel):
    title: str


class ContentSave(BaseModel):
    content: str
    source: str = "editor"  # 'editor' | 'paste'


# Response schemas
class DocumentResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    share_mode: str
    version_count: int = 0
    latest_version: int | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentDetail(DocumentResponse):
    content: str | None = None  # latest version content


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int
