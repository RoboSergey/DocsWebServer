from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401 — ensures models are registered on Base.metadata
from app.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="Document Web Server", lifespan=lifespan)


# Will mount static files and templates in later phases
# For now, just health check
@app.get("/health")
async def health():
    return {"status": "ok"}
