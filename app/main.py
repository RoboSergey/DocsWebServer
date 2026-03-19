from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401 — ensures models are registered on Base.metadata
from app.database import create_tables
from app.routers.documents import router as documents_router
from app.routers.pages import router as pages_router
from app.routers.sharing import router as sharing_router
from app.routers.versions import router as versions_router
from app.templates_config import templates  # noqa: F401 — ensures templates are initialized


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="Document Web Server", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(documents_router)
app.include_router(versions_router)
app.include_router(sharing_router)
app.include_router(pages_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
