from fastapi import APIRouter, File, Request, UploadFile

from app.api.deps import current_session
from app.core.config import settings
from app.core.exceptions import MSG_DB_CONNECT_SOON, AppError
from app.infra.session_store import store
from app.schemas.payloads import DbConnectRequest
from app.services.dataframe_ops import df_preview
from app.services.ingestion import ingest_upload

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload")
async def upload_dataset(request: Request, file: UploadFile = File(...)) -> dict:
    session = current_session(request)
    raw = await file.read()
    df, meta = ingest_upload(file.filename or "dataset.csv", raw)
    store.set_dataframe(session, df, file.filename or "dataset.csv", meta)
    return {"meta": meta, "preview": df_preview(df, settings.preview_rows)}


@router.get("/preview")
async def preview(request: Request) -> dict:
    session = current_session(request)
    if session.df is None:
        return {
            "file_name": None,
            "meta": None,
            "preview": None,
            "undo_depth": 0,
            "columns": [],
        }
    return {
        "file_name": session.file_name,
        "meta": session.ingest_meta,
        "preview": df_preview(session.df, settings.preview_rows),
        "undo_depth": len(session.history),
        "columns": list(session.df.columns),
    }


_DB_ENGINES = {"postgresql", "mysql", "sqlite"}


@router.post("/db-connect")
async def db_connect(_request: Request, body: DbConnectRequest) -> dict:
    engine = (body.engine or "").strip().lower()
    if engine not in _DB_ENGINES:
        raise AppError("Motor no reconocido. Usa PostgreSQL, MySQL o SQLite.", 400)
    raise AppError(MSG_DB_CONNECT_SOON, 501)
