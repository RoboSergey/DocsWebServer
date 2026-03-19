from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid
from passlib.context import CryptContext

from app.dependencies import get_db, get_admin_user
from app.models import User, Document, Folder
from app.schemas import UserCreate, UserResponse, PasswordReset

router = APIRouter(prefix="/api/admin", tags=["admin"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        id=str(uuid.uuid4()),
        username=body.username,
        password=pwd_context.hash(body.password),
        is_admin=body.is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Hard-delete: ORM cascade deletes versions automatically when documents are deleted
    await db.execute(delete(Document).where(Document.user_id == user_id))
    await db.execute(delete(Folder).where(Folder.user_id == user_id))
    await db.delete(user)
    await db.commit()


@router.post("/users/{user_id}/reset-password", status_code=204)
async def reset_password(
    user_id: str,
    body: PasswordReset,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = pwd_context.hash(body.password)
    await db.commit()
