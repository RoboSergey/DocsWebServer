import pytest
import pytest_asyncio
import jwt
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.main import app as fastapi_app
from app.database import Base
from app.dependencies import get_db
from app.config import settings


@pytest_asyncio.fixture
async def auth_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Seed a test user directly in the DB
    from passlib.context import CryptContext
    import uuid
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with session_factory() as db:
        user_id = str(uuid.uuid4())
        hashed = pwd_context.hash("correctpassword")
        await db.execute(
            text("INSERT INTO users (id, username, password, is_admin) VALUES (:id, :u, :p, :a)"),
            {"id": user_id, "u": "testuser", "p": hashed, "a": False}
        )
        await db.commit()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, user_id  # yield both client and user_id for use in tests

    fastapi_app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest.mark.asyncio
async def test_login_success(auth_client):
    client, _ = auth_client
    res = await client.post("/api/auth/login", json={"username": "testuser", "password": "correctpassword"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(auth_client):
    client, _ = auth_client
    res = await client.post("/api/auth/login", json={"username": "testuser", "password": "wrongpassword"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(auth_client):
    client, _ = auth_client
    res = await client.post("/api/auth/login", json={"username": "nobody", "password": "anything"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_documents_no_token(auth_client):
    client, _ = auth_client
    res = await client.get("/api/documents")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_documents_expired_token(auth_client):
    client, _ = auth_client
    expired_payload = {
        "sub": "some-user-id",
        "is_admin": False,
        "exp": datetime.now(timezone.utc) - timedelta(days=1),
    }
    token = jwt.encode(expired_payload, settings.secret_key, algorithm="HS256")
    res = await client.get("/api/documents", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_admin_endpoint_non_admin(auth_client):
    """Non-admin user gets 403 on admin endpoints."""
    client, _ = auth_client
    # First login to get a real token
    login_res = await client.post("/api/auth/login", json={"username": "testuser", "password": "correctpassword"})
    token = login_res.json()["access_token"]
    res = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_login_sets_correct_payload(auth_client):
    """JWT payload has sub, is_admin, exp fields."""
    client, user_id = auth_client
    res = await client.post("/api/auth/login", json={"username": "testuser", "password": "correctpassword"})
    token = res.json()["access_token"]
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["sub"] == user_id
    assert payload["is_admin"] is False
    assert "exp" in payload
