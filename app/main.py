from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401 — ensures models are registered on Base.metadata
from app.database import create_tables
from app.routers.documents import router as documents_router
from app.routers.versions import router as versions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="Document Web Server", lifespan=lifespan)

app.include_router(documents_router)
app.include_router(versions_router)


# Will mount static files and templates in later phases
# For now, just health check
@app.get("/health")
async def health():
    return {"status": "ok"}
