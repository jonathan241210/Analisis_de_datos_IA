from pandas import DataFrame

from app.sandbox.extract import extract_python_code
from app.services.copilot.context_builder import build_context, route_specialist
from app.services.copilot.gemini_client import generate_reply
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


async def chat_turn(df: DataFrame, user_query: str, history: list[dict[str, str]], active_tab: str) -> dict:
    specialist = route_specialist(user_query, active_tab)
    context = build_context(df, user_query)
    user_message = build_user_message(user_query, context, active_tab)
    reply = await generate_reply(PROMPTS[specialist], user_message, history)
    return {
        "specialist": specialist,
        "content": reply,
        "code_blocks": extract_python_code(reply),
    }
