import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.database_path}",
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_tables():
    # Ensure all models are registered to Base before create_all
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for sql in [
            "ALTER TABLE documents ADD COLUMN folder_id TEXT REFERENCES folders(id)",
            "ALTER TABLE folders ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE documents ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE documents ADD COLUMN user_id TEXT REFERENCES users(id)",
            "ALTER TABLE folders ADD COLUMN user_id TEXT REFERENCES users(id)",
        ]:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass  # column already exists

    # Seed admin user on first startup
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with async_session_maker() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        if count == 0:
            admin_id = str(uuid.uuid4())
            hashed = pwd_context.hash("admin")
            await db.execute(
                text("INSERT INTO users (id, username, password, is_admin) VALUES (:id, :username, :password, :is_admin)"),
                {"id": admin_id, "username": "admin", "password": hashed, "is_admin": True}
            )
            await db.commit()
        else:
            result = await db.execute(text("SELECT id FROM users WHERE username = 'admin'"))
            row = result.fetchone()
            admin_id = row[0] if row else None

        # Backfill always runs (if we have an admin to assign to)
        if admin_id:
            await db.execute(
                text("UPDATE documents SET user_id = :id WHERE user_id IS NULL"),
                {"id": admin_id}
            )
            await db.execute(
                text("UPDATE folders SET user_id = :id WHERE user_id IS NULL"),
                {"id": admin_id}
            )
            await db.commit()

        # Default password warning — always check, not just in else branch
        result = await db.execute(text("SELECT password FROM users WHERE username = 'admin'"))
        row = result.fetchone()
        if row and pwd_context.verify("admin", row[0]):
            print("WARNING: Default admin password is still in use. Change it via the admin panel.")
