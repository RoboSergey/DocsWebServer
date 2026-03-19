from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext

from app.dependencies import get_db
from app.models import User
from app.schemas import TokenResponse
from app.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DUMMY_HASH = "$2b$12$eImiTXuWVxfM37uY4JANjQ.NptiOh7JBn5n1o8EBL.xXQpjOlS3zK"

class _LoginBody(BaseModel):
    username: str
    password: str

@router.post("/login", response_model=TokenResponse)
async def login(body: _LoginBody, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    # Always run bcrypt to prevent timing oracle
    password_to_check = user.password if user is not None else DUMMY_HASH
    if user is None or not pwd_context.verify(body.password, password_to_check):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    expire = datetime.now(timezone.utc) + timedelta(days=settings.token_expire_days)
    token = jwt.encode(
        {"sub": user.id, "is_admin": user.is_admin, "exp": expire},
        settings.secret_key,
        algorithm="HS256",
    )
    return TokenResponse(access_token=token)
