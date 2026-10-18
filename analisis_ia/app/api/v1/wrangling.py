from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.api.deps import current_session
from app.core.config import settings
from app.infra.session_store import store
from app.schemas.payloads import WranglingRequest
from app.services.dataframe_ops import df_preview, df_to_csv_bytes
from app.services.wrangling import apply_wrangling

router = APIRouter(prefix="/wrangling", tags=["wrangling"])


def _preview_payload(session) -> dict:
    return {
        "preview": df_preview(session.df, settings.preview_rows) if session.df is not None else None,
        "undo_depth": len(session.history),
        "columns": list(session.df.columns) if session.df is not None else [],
    }


@router.post("/apply")
async def apply_op(request: Request, body: WranglingRequest) -> dict:
    session = store.require_df(current_session(request))
    new_df = apply_wrangling(
        session.df,
        body.op,
        columns=body.columns,
        strategy=body.strategy or "Media",
        value=body.value,
        target_type=body.target_type or "string",
        method=body.method or "StandardScaler",
        new_name=body.new_name,
        decimals=body.decimals,
    )
    store.push_and_set(session, new_df)
    return _preview_payload(session)


@router.post("/undo")
async def undo(request: Request) -> dict:
    session = store.require_df(current_session(request))
    ok = store.undo(session)
    return {"undone": ok, **_preview_payload(session)}


@router.post("/reset")
async def reset(request: Request) -> dict:
    session = store.require_df(current_session(request))
    ok = store.reset(session)
    return {"reset": ok, **_preview_payload(session)}


@router.get("/export")
async def export_csv(request: Request) -> Response:
    session = store.require_df(current_session(request))
    data = df_to_csv_bytes(session.df)
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dataset_transformado.csv"},
    )
