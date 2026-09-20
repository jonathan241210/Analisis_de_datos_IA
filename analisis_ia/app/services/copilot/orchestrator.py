from pandas import DataFrame

from app.domain.models import AnalysisSession
from app.sandbox.extract import extract_python_code
from app.services.copilot.context_builder import build_context, route_specialist
from app.services.copilot.llm_router import generate_reply_routed
from app.services.copilot.prompts import (
    CLEANING_PROMPT,
    EDA_PROMPT,
    ML_PROMPT,
    build_user_message,
)

PROMPTS = {
    "cleaning": CLEANING_PROMPT,
    "eda": EDA_PROMPT,
    "ml": ML_PROMPT,
}


async def chat_turn(
    df: DataFrame,
    user_query: str,
    history: list[dict[str, str]],
    active_tab: str,
    session: AnalysisSession | None = None,
) -> dict:
    specialist = route_specialist(user_query, active_tab)
    context = build_context(df, user_query)
    user_message = build_user_message(user_query, context, active_tab)
    if session is None:
        raise RuntimeError("chat_turn requires a session for LLM routing")
    reply, fallback = await generate_reply_routed(session, PROMPTS[specialist], user_message, history)
    result = {
        "specialist": specialist,
        "content": reply,
        "code_blocks": extract_python_code(reply),
    }
    if fallback:
        result["fallback"] = fallback
        result["llm"] = {
            "active_id": session.llm_active_id,
            "active_label": fallback["to_label"],
            "active_model": fallback["to_model"],
        }
    return result
