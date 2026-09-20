from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.exceptions import AppError
from app.domain.models import AnalysisSession
from app.services.copilot.errors import MSG_GENERIC, MSG_TOKENS, classify_llm_error
from app.services.copilot.gemini_client import GeminiUnavailable, ModelTurn, generate_reply, generate_with_tools
from app.services.copilot.llm_slots import (
    catalog_row,
    ensure_llm,
    ordered_slot_ids,
    public_settings,
    resolve_key,
    slot_ready,
)
from app.services.copilot.tools import TOOL_SPECS

logger = logging.getLogger("analisis_ia")

_HTTP_TIMEOUT = httpx.Timeout(45.0, connect=10.0)


def _tools_openai() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
        for spec in TOOL_SPECS
    ]


def _tools_anthropic() -> list[dict[str, Any]]:
    return [
        {
            "name": spec["name"],
            "description": spec["description"],
            "input_schema": spec["parameters"],
        }
        for spec in TOOL_SPECS
    ]


def _dump_tool_result(row: dict[str, Any]) -> str:
    payload = row.get("response") or {}
    return json.dumps(payload, ensure_ascii=False, default=str)


def _openai_messages(system_prompt: str, generic: list[dict[str, Any]], history: list[dict[str, str]] | None = None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-6:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content") or ""})
    for item in generic or []:
        role = item.get("role")
        if role == "user":
            messages.append({"role": "user", "content": item.get("text") or ""})
        elif role == "model":
            msg: dict[str, Any] = {"role": "assistant", "content": item.get("text") or None}
            calls = item.get("calls") or []
            if calls:
                msg["tool_calls"] = []
                for i, call in enumerate(calls):
                    cid = str(call.get("call_id") or f"call_{call.get('name')}_{i}")
                    msg["tool_calls"].append({
                        "id": cid,
                        "type": "function",
                        "function": {
                            "name": call.get("name") or "",
                            "arguments": json.dumps(call.get("args") or {}, ensure_ascii=False),
                        },
                    })
            messages.append(msg)
        elif role == "tool":
            results = item.get("results") or []
            for i, row in enumerate(results):
                cid = str(row.get("call_id") or f"call_{row.get('name')}_{i}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": cid,
                    "content": _dump_tool_result(row),
                })
    return messages


def _anthropic_payload(system_prompt: str, generic: list[dict[str, Any]], history: list[dict[str, str]] | None = None) -> tuple[str, list[dict[str, Any]]]:
    messages: list[dict[str, Any]] = []
    if history:
        for msg in history[-6:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content") or ""})
    for item in generic or []:
        role = item.get("role")
        if role == "user":
            messages.append({"role": "user", "content": item.get("text") or ""})
        elif role == "model":
            blocks: list[dict[str, Any]] = []
            text = item.get("text") or ""
            if text:
                blocks.append({"type": "text", "text": text})
            for i, call in enumerate(item.get("calls") or []):
                cid = str(call.get("call_id") or f"tool_{call.get('name')}_{i}")
                blocks.append({
                    "type": "tool_use",
                    "id": cid,
                    "name": call.get("name") or "",
                    "input": call.get("args") or {},
                })
            if not blocks:
                blocks.append({"type": "text", "text": ""})
            messages.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            blocks = []
            for i, row in enumerate(item.get("results") or []):
                cid = str(row.get("call_id") or f"tool_{row.get('name')}_{i}")
                blocks.append({
                    "type": "tool_result",
                    "tool_use_id": cid,
                    "content": _dump_tool_result(row),
                })
            if blocks:
                messages.append({"role": "user", "content": blocks})
    return system_prompt, messages


def _raise_http(provider: str, status: int, body: str) -> None:
    classified = classify_llm_error(None, extra=f"{status} {body}")
    logger.warning("%s generate failed (%s)", provider, status)
    raise GeminiUnavailable(classified)


async def _openai_chat(
    *,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    with_tools: bool,
) -> ModelTurn:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 4096,
    }
    if with_tools:
        payload["tools"] = _tools_openai()
        payload["tool_choice"] = "auto"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    except GeminiUnavailable:
        raise
    except Exception as exc:
        logger.exception("OpenAI request failed")
        raise GeminiUnavailable(classify_llm_error(exc)) from exc
    if res.status_code >= 400:
        _raise_http("openai", res.status_code, res.text)
    data = res.json()
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    text = message.get("content") or ""
    calls: list[dict[str, Any]] = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        raw_args = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        except json.JSONDecodeError:
            args = {}
        calls.append({
            "name": str(fn.get("name") or ""),
            "args": args if isinstance(args, dict) else {},
            "call_id": str(tc.get("id") or ""),
        })
    turn = ModelTurn(text=text if isinstance(text, str) else "", calls=calls)
    if not turn.text and not turn.calls:
        logger.warning("OpenAI returned empty turn")
        raise GeminiUnavailable()
    return turn


async def _anthropic_chat(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    messages: list[dict[str, Any]],
    with_tools: bool,
) -> ModelTurn:
    payload: dict[str, Any] = {
        "model": model,
        "system": system_prompt,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.3,
    }
    if with_tools:
        payload["tools"] = _tools_anthropic()
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            res = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
    except GeminiUnavailable:
        raise
    except Exception as exc:
        logger.exception("Anthropic request failed")
        raise GeminiUnavailable(classify_llm_error(exc)) from exc
    if res.status_code >= 400:
        _raise_http("anthropic", res.status_code, res.text)
    data = res.json()
    text_parts: list[str] = []
    calls: list[dict[str, Any]] = []
    for block in data.get("content") or []:
        btype = block.get("type")
        if btype == "text":
            text_parts.append(block.get("text") or "")
        elif btype == "tool_use":
            raw_input = block.get("input") or {}
            calls.append({
                "name": str(block.get("name") or ""),
                "args": raw_input if isinstance(raw_input, dict) else {},
                "call_id": str(block.get("id") or ""),
            })
    turn = ModelTurn(text="".join(text_parts).strip(), calls=calls)
    if not turn.text and not turn.calls:
        logger.warning("Anthropic returned empty turn")
        raise GeminiUnavailable()
    return turn


async def _call_slot(
    slot: dict[str, str],
    *,
    system_prompt: str,
    user_message: str | None,
    history: list[dict[str, str]] | None,
    generic_contents: list[dict[str, Any]] | None,
    with_tools: bool,
) -> ModelTurn:
    key = resolve_key(slot)
    model = (slot.get("model") or "").strip()
    sid = slot["id"]
    if not key or not model:
        label = catalog_row(sid)["label"]
        raise AppError(
            f"Falta la clave de API de {label}. Pégala en Ajustes o usa la del servidor.",
            400,
        )
    if sid == "gemini":
        if with_tools:
            return await generate_with_tools(
                system_prompt,
                generic_contents or [],
                model=model,
                api_key=key,
            )
        return ModelTurn(text=await generate_reply(
            system_prompt,
            user_message or "",
            history or [],
            model=model,
            api_key=key,
        ))
    if sid == "openai":
        if with_tools:
            messages = _openai_messages(system_prompt, generic_contents or [])
        else:
            messages = _openai_messages(system_prompt, [], history)
            messages.append({"role": "user", "content": user_message or ""})
        return await _openai_chat(api_key=key, model=model, messages=messages, with_tools=with_tools)
    if sid == "anthropic":
        if with_tools:
            system, messages = _anthropic_payload(system_prompt, generic_contents or [])
        else:
            system, messages = _anthropic_payload(system_prompt, [], history)
            messages.append({"role": "user", "content": user_message or ""})
        return await _anthropic_chat(
            api_key=key,
            model=model,
            system_prompt=system,
            messages=messages,
            with_tools=with_tools,
        )
    raise AppError("Proveedor desconocido.", 400)


def _fallback_event(from_id: str, to_id: str, to_model: str) -> dict[str, str]:
    return {
        "from_id": from_id,
        "from_label": catalog_row(from_id)["label"],
        "to_id": to_id,
        "to_label": catalog_row(to_id)["label"],
        "to_model": to_model,
    }


async def _with_fallback(
    session: AnalysisSession,
    *,
    system_prompt: str,
    user_message: str | None = None,
    history: list[dict[str, str]] | None = None,
    generic_contents: list[dict[str, Any]] | None = None,
    with_tools: bool = False,
) -> tuple[ModelTurn, dict[str, str] | None]:
    ensure_llm(session)
    origin = session.llm_active_id
    last_exc: BaseException | None = None
    tried = 0
    for sid in ordered_slot_ids(session):
        slot = session.llm_slots[sid]
        if not slot_ready(slot):
            continue
        tried += 1
        try:
            turn = await _call_slot(
                slot,
                system_prompt=system_prompt,
                user_message=user_message,
                history=history,
                generic_contents=generic_contents,
                with_tools=with_tools,
            )
        except GeminiUnavailable as exc:
            last_exc = exc
            if exc.message != MSG_TOKENS:
                raise
            logger.warning("LLM quota on %s; trying next slot", sid)
            continue
        except AppError:
            raise
        fallback = None
        if sid != origin:
            session.llm_active_id = sid
            fallback = _fallback_event(origin, sid, slot.get("model") or "")
            logger.info("LLM fallback %s -> %s", origin, sid)
        return turn, fallback
    if last_exc is not None:
        raise last_exc
    if tried == 0:
        label = catalog_row(origin)["label"]
        raise AppError(
            f"Falta la clave de API de {label}. Pégala en Ajustes o usa la del servidor.",
            400,
        )
    raise GeminiUnavailable(MSG_GENERIC)


async def generate_reply_routed(
    session: AnalysisSession,
    system_prompt: str,
    user_message: str,
    history: list[dict[str, str]],
) -> tuple[str, dict[str, str] | None]:
    turn, fallback = await _with_fallback(
        session,
        system_prompt=system_prompt,
        user_message=user_message,
        history=history,
        with_tools=False,
    )
    return turn.text, fallback


async def generate_with_tools_routed(
    session: AnalysisSession,
    system_prompt: str,
    generic_contents: list[dict[str, Any]],
) -> tuple[ModelTurn, dict[str, str] | None]:
    return await _with_fallback(
        session,
        system_prompt=system_prompt,
        generic_contents=generic_contents,
        with_tools=True,
    )


def settings_view(session: AnalysisSession) -> dict[str, Any]:
    return public_settings(session)
