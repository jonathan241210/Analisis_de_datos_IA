from app.core.config import settings
from app.core.exceptions import AppError


class GeminiUnavailable(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)


async def generate_reply(system_prompt: str, user_message: str, history: list[dict[str, str]]) -> str:
    if not settings.gemini_api_key:
        raise GeminiUnavailable(
            "Falta GEMINI_API_KEY en analisis_ia/.env. Las herramientas estáticas siguen disponibles."
        )
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise GeminiUnavailable("El paquete google-genai no está instalado.") from exc

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
    except Exception as exc:
        raise GeminiUnavailable(f"Gemini no respondió: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise GeminiUnavailable("Respuesta vacía de Gemini.")
    return text
