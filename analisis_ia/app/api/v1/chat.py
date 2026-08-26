from fastapi import APIRouter, Request

from app.api.deps import current_session
from app.core.config import settings
from app.infra.session_store import store
from app.sandbox.executor import run_generated_code
from app.schemas.payloads import ChatRequest, ExecuteRequest
from app.services.copilot.orchestrator import chat_turn
from app.services.dataframe_ops import df_preview

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message")
async def message(request: Request, body: ChatRequest) -> dict:
    session = store.require_df(current_session(request))
    result = await chat_turn(session.df, body.message, session.chat_history, body.tab)
    session.chat_history.append({"role": "user", "content": body.message})
    session.chat_history.append({"role": "assistant", "content": result["content"]})
    result["history"] = session.chat_history
    return result


@router.post("/execute")
async def execute(request: Request, body: ExecuteRequest) -> dict:
    session = store.require_df(current_session(request))
    original = session.df
    result = run_generated_code(body.code, original)
    payload = {
        "success": result.success,
        "error": result.error,
        "stdout": result.stdout,
        "fig": result.fig,
        "mutated": False,
        "preview": None,
        "display": None,
    }
    if result.success and result.display_df is not None:
        payload["display"] = df_preview(result.display_df, min(50, len(result.display_df)))
    if result.success and result.df is not None and not result.df.equals(original):
        store.push_and_set(session, result.df)
        payload["mutated"] = True
        payload["preview"] = df_preview(session.df, settings.preview_rows)
    return payload


@router.get("/history")
async def history(request: Request) -> dict:
    session = current_session(request)
    return {"history": session.chat_history}
