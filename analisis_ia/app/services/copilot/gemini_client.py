import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.exceptions import AppError
from app.services.copilot.errors import MSG_GENERIC, classify_gemini_error
from app.services.copilot.tools import TOOL_SPECS

logger = logging.getLogger("analisis_ia")


class GeminiUnavailable(AppError):
    def __init__(self, message: str = MSG_GENERIC) -> None:
        super().__init__(message, status_code=503)


@dataclass
class ModelTurn:
    text: str = ""
    calls: list[dict[str, Any]] = field(default_factory=list)
    raw_model_content: Any = None


def _import_genai():
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.exception("google-genai is not installed")
        raise GeminiUnavailable() from None
    return genai, types


def _client(api_key: str | None = None):
    key = (api_key or settings.gemini_api_key or "").strip()
    if not key:
        logger.warning("GEMINI_API_KEY missing; chat unavailable")
        raise GeminiUnavailable()
    genai, types = _import_genai()
    return genai.Client(api_key=key), types


def _raise_gemini(exc: BaseException) -> None:
    logger.exception("Gemini generate_content failed")
    raise GeminiUnavailable(classify_gemini_error(exc)) from exc


def _function_declaration(types, spec: dict[str, Any]):
    kwargs = {"name": spec["name"], "description": spec["description"]}
    schema = spec["parameters"]
    try:
        return types.FunctionDeclaration(parameters_json_schema=schema, **kwargs)
    except TypeError:
        return types.FunctionDeclaration(parameters=schema, **kwargs)


def _tools_config(types):
    decls = [_function_declaration(types, spec) for spec in TOOL_SPECS]
    tool = types.Tool(function_declarations=decls)
    kwargs: dict[str, Any] = {
        "temperature": 0.3,
        "max_output_tokens": 4096,
        "tools": [tool],
    }
    afc = getattr(types, "AutomaticFunctionCallingConfig", None)
    if afc is not None:
        kwargs["automatic_function_calling"] = afc(disable=True)
    return kwargs


def _history_contents(types, history: list[dict[str, str]]) -> list:
    contents = []
    for msg in history[-6:]:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg.get("content", ""))]))
    return contents


def _generic_to_genai(types, generic: list[dict[str, Any]]):
    out = []
    for item in generic:
        if item.get("raw") is not None:
            out.append(item["raw"])
            continue
        role = item.get("role")
        if role == "user":
            out.append(types.Content(role="user", parts=[types.Part.from_text(text=item.get("text") or "")]))
        elif role == "model":
            parts = []
            text = item.get("text") or ""
            if text:
                parts.append(types.Part.from_text(text=text))
            for call in item.get("calls") or []:
                try:
                    parts.append(types.Part.from_function_call(name=call["name"], args=call.get("args") or {}))
                except Exception:
                    parts.append(types.Part.from_text(text=f"[tool {call.get('name')}]"))
            if not parts:
                parts.append(types.Part.from_text(text=""))
            out.append(types.Content(role="model", parts=parts))
        elif role == "tool":
            parts = [
                types.Part.from_function_response(name=row["name"], response=row.get("response") or {})
                for row in item.get("results") or []
            ]
            if parts:
                # Gemini 3.x rejects role "tool"; function results are a user turn.
                out.append(types.Content(role="user", parts=parts))
    return out


def _parse_turn(response) -> ModelTurn:
    text = getattr(response, "text", None) or ""
    calls: list[dict[str, Any]] = []
    raw = None
    candidates = getattr(response, "candidates", None) or []
    if candidates:
        raw = getattr(candidates[0], "content", None)
    fcs = getattr(response, "function_calls", None) or []
    for fc in fcs:
        inner = getattr(fc, "function_call", None) or fc
        name = getattr(inner, "name", None) or getattr(fc, "name", "")
        args = getattr(inner, "args", None) or getattr(fc, "args", None) or {}
        calls.append({"name": str(name), "args": dict(args) if args else {}})
    if not calls and raw is not None:
        for part in getattr(raw, "parts", None) or []:
            fc = getattr(part, "function_call", None)
            if fc is None:
                continue
            args = getattr(fc, "args", None) or {}
            calls.append({"name": str(fc.name), "args": dict(args) if args else {}})
    return ModelTurn(text=text, calls=calls, raw_model_content=raw)


async def generate_reply(
    system_prompt: str,
    user_message: str,
    history: list[dict[str, str]],
    *,
    model: str | None = None,
    api_key: str | None = None,
) -> str:
    client, types = _client(api_key=api_key)
    contents = _history_contents(types, history)
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
    model_name = (model or settings.gemini_model or "").strip()
    try:
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=4096,
            ),
        )
    except Exception as exc:
        _raise_gemini(exc)
        raise
    text = getattr(response, "text", None)
    if not text:
        logger.warning("Gemini returned empty text")
        raise GeminiUnavailable()
    return text


async def generate_with_tools(
    system_prompt: str,
    generic_contents: list[dict[str, Any]],
    *,
    model: str | None = None,
    api_key: str | None = None,
) -> ModelTurn:
    client, types = _client(api_key=api_key)
    contents = _generic_to_genai(types, generic_contents)
    config_kwargs = _tools_config(types)
    config_kwargs["system_instruction"] = system_prompt
    model_name = (model or settings.gemini_model or "").strip()
    try:
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )
    except Exception as exc:
        _raise_gemini(exc)
        raise
    turn = _parse_turn(response)
    if not turn.text and not turn.calls:
        logger.warning("Gemini returned empty agent turn")
        raise GeminiUnavailable()
    return turn
