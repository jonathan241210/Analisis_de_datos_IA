from fastapi import APIRouter, File, Request, UploadFile

from app.api.deps import current_session
from app.core.config import settings
from app.infra.session_store import store
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
