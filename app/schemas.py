from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Request schemas
class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(default="", max_length=10_000_000)  # optional initial content
    folder_id: str | None = None


class DocumentUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


class ContentSave(BaseModel):
    content: str = Field(..., max_length=10_000_000)
    source: Literal["editor", "paste"] = "editor"


# Response schemas
class DocumentResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    share_mode: str
    folder_id: str | None = None
    version_count: int = 0
    latest_version: int | None = None
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)


class DocumentDetail(DocumentResponse):
    content: str | None = None  # latest version content


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class VersionResponse(BaseModel):
    id: int
    document_id: str
    version_num: int
    created_at: datetime
    source: str

    model_config = ConfigDict(from_attributes=True)


class VersionDetail(VersionResponse):
    content: str


class VersionListResponse(BaseModel):
    versions: list[VersionResponse]
    total: int


class ShareSettings(BaseModel):
    share_mode: Literal["public", "token"]
    share_token: str | None
    share_url: str | None = None  # computed by router

    model_config = ConfigDict(from_attributes=True)


class ShareUpdate(BaseModel):
    share_mode: Literal["public", "token"]


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: str | None = None


class FolderRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class FolderResponse(BaseModel):
    id: str
    name: str
    parent_id: str | None = None
    created_at: datetime
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)


class FolderTree(FolderResponse):
    children: list["FolderTree"] = []
    documents: list[DocumentResponse] = []


# Required: Pydantic v2 needs model_rebuild() for self-referential models
FolderTree.model_rebuild()


class DocumentPosition(BaseModel):
    folder_id: str | None = None
    sort_order: int = Field(..., ge=0)


class FolderPosition(BaseModel):
    parent_id: str | None = None
    sort_order: int = Field(..., ge=0)


class DocumentMove(BaseModel):
    folder_id: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)
    is_admin: bool = False


class UserResponse(BaseModel):
    id: str
    username: str
    is_admin: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PasswordReset(BaseModel):
    password: str = Field(..., min_length=1, max_length=200)
