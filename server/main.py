from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from server.api.calls import router as calls_router
from server.api.config import router as config_router
from server.db.base import Base
from server.db.session import engine
from server.settings import settings
from server.ws.signaling_ws import router as ws_router

import server.models.call  # noqa: F401 — регистрация моделей в metadata


def _ensure_calls_media_column() -> None:
    """Добавить колонку media к существующей таблице calls (create_all не меняет схему)."""
    try:
        insp = inspect(engine)
        if not insp.has_table("calls"):
            return
        cols = {c["name"] for c in insp.get_columns("calls")}
        if "media" in cols:
            return
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE calls ADD COLUMN media VARCHAR(16) NOT NULL DEFAULT 'audio'"))
    except Exception:
        pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_calls_media_column()
    yield


app = FastAPI(
    title="MeetService",
    description="Сигналинг WebRTC (1:1), JWT как у ChatService",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calls_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
