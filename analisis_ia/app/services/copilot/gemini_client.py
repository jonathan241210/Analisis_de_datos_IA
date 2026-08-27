import logging

from app.core.config import settings
from app.core.exceptions import AppError

logger = logging.getLogger("analisis_ia")


class GeminiUnavailable(AppError):
    def __init__(self, message: str = "La IA no responde") -> None:
        super().__init__(message, status_code=503)


async def generate_reply(system_prompt: str, user_message: str, history: list[dict[str, str]]) -> str:
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY missing; chat unavailable")
        raise GeminiUnavailable()
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.exception("google-genai is not installed")
        raise GeminiUnavailable() from None

    client = genai.Client(api_key=settings.gemini_api_key)
    contents: list = []
    for msg in history[-6:]:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg.get("content", ""))]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=4096,
            ),
        )
    except Exception:
        logger.exception("Gemini generate_content failed")
        raise GeminiUnavailable() from None

    text = getattr(response, "text", None)
    if not text:
        logger.warning("Gemini returned empty text")
        raise GeminiUnavailable()
    return text
