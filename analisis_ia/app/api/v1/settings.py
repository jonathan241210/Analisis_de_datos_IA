from fastapi import APIRouter, Request

from app.api.deps import current_session
from app.schemas.payloads import LlmSettingsUpdate
from app.services.copilot.llm_slots import apply_settings, public_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/llm")
async def get_llm_settings(request: Request) -> dict:
    session = current_session(request)
    return public_settings(session)


@router.post("/llm")
async def post_llm_settings(request: Request, body: LlmSettingsUpdate) -> dict:
    session = current_session(request)
    return apply_settings(session, body.active_id, body.slots)
