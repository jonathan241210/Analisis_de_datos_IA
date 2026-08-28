import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.deps import current_session
from app.core.config import settings
from app.infra.session_store import store
from app.sandbox.executor import run_generated_code
from app.schemas.payloads import AgentApplyRequest, ChatRequest, ExecuteRequest
from app.services.copilot.agent_loop import run_agent_loop
from app.services.copilot.errors import MSG_GENERIC
from app.services.copilot.gemini_client import GeminiUnavailable
from app.services.copilot.orchestrator import chat_turn
from app.services.copilot.tools import apply_confirmed_action
from app.services.dataframe_ops import df_preview

router = APIRouter(prefix="/chat", tags=["chat"])


def trim_last_turn(history: list[dict[str, str]]) -> None:
    if history and history[-1].get("role") == "assistant":
        history.pop()
    if history and history[-1].get("role") == "user":
        history.pop()


@router.post("/message")
async def message(request: Request, body: ChatRequest) -> dict:
    session = store.require_df(current_session(request))
    if body.replace_last:
        trim_last_turn(session.chat_history)
    result = await chat_turn(session.df, body.message, session.chat_history, body.tab)
    session.chat_history.append({"role": "user", "content": body.message})
    session.chat_history.append({"role": "assistant", "content": result["content"]})
    result["history"] = session.chat_history
    return result


@router.post("/agent")
async def agent_message(request: Request, body: ChatRequest) -> StreamingResponse:
    session = store.require_df(current_session(request))
    if body.replace_last:
        trim_last_turn(session.chat_history)

    async def events():
        try:
            async for ev in run_agent_loop(session.df, body.message, session.chat_history, body.tab):
                if ev.get("type") == "final":
                    session.chat_history.append({"role": "user", "content": body.message})
                    session.chat_history.append({"role": "assistant", "content": ev.get("content") or ""})
                    ev["history"] = session.chat_history
                yield json.dumps(ev, ensure_ascii=False, default=str) + "\n"
        except GeminiUnavailable as exc:
            yield json.dumps({"type": "error", "detail": exc.message}, ensure_ascii=False) + "\n"
        except Exception:
            yield json.dumps({"type": "error", "detail": MSG_GENERIC}, ensure_ascii=False) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


@router.post("/apply")
async def apply_agent_action(request: Request, body: AgentApplyRequest) -> dict:
    session = store.require_df(current_session(request))
    original = session.df
    new_df = apply_confirmed_action(session.df, body.model_dump())
    mutated = not new_df.equals(original)
    if mutated:
        store.push_and_set(session, new_df)
    return {
        "success": True,
        "mutated": mutated,
        "preview": df_preview(session.df, settings.preview_rows),
        "undo_depth": len(session.history),
        "columns": list(session.df.columns),
    }


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
