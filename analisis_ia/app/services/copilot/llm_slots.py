from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.exceptions import AppError
from app.domain.models import AnalysisSession

SLOT_CATALOG: tuple[dict[str, str], ...] = (
    {"id": "gemini", "provider": "gemini", "label": "Google Gemini"},
    {"id": "openai", "provider": "openai", "label": "OpenAI"},
    {"id": "anthropic", "provider": "anthropic", "label": "Anthropic"},
)

_VALID_IDS = {row["id"] for row in SLOT_CATALOG}
_KEY_MODES = {"builtin", "user"}


def _default_model(slot_id: str) -> str:
    if slot_id == "openai":
        return (settings.openai_model or "gpt-4o-mini").strip()
    if slot_id == "anthropic":
        return (settings.anthropic_model or "claude-sonnet-4-5").strip()
    return (settings.gemini_model or "gemini-2.0-flash").strip()


def builtin_key(slot_id: str) -> str:
    if slot_id == "openai":
        return (settings.openai_api_key or "").strip()
    if slot_id == "anthropic":
        return (settings.anthropic_api_key or "").strip()
    return (settings.gemini_api_key or "").strip()


def _empty_slot(slot_id: str) -> dict[str, str]:
    has_builtin = bool(builtin_key(slot_id))
    return {
        "id": slot_id,
        "model": _default_model(slot_id),
        "key_mode": "builtin" if has_builtin else "user",
        "user_api_key": "",
    }


def ensure_llm(session: AnalysisSession) -> AnalysisSession:
    if not session.llm_slots:
        session.llm_slots = {row["id"]: _empty_slot(row["id"]) for row in SLOT_CATALOG}
    for row in SLOT_CATALOG:
        sid = row["id"]
        if sid not in session.llm_slots:
            session.llm_slots[sid] = _empty_slot(sid)
        slot = session.llm_slots[sid]
        slot.setdefault("id", sid)
        slot.setdefault("model", _default_model(sid))
        slot.setdefault("key_mode", "builtin" if builtin_key(sid) else "user")
        slot.setdefault("user_api_key", "")
        if slot["key_mode"] not in _KEY_MODES:
            slot["key_mode"] = "builtin"
        if not (slot.get("model") or "").strip():
            slot["model"] = _default_model(sid)
    if session.llm_active_id not in _VALID_IDS:
        session.llm_active_id = "gemini"
    return session


def resolve_key(slot: dict[str, str]) -> str:
    user = (slot.get("user_api_key") or "").strip()
    builtin = builtin_key(slot["id"])
    if slot.get("key_mode") == "user":
        return user
    return builtin or user


def slot_ready(slot: dict[str, str]) -> bool:
    return bool(resolve_key(slot) and (slot.get("model") or "").strip())


def catalog_row(slot_id: str) -> dict[str, str]:
    for row in SLOT_CATALOG:
        if row["id"] == slot_id:
            return row
    raise AppError("Proveedor desconocido.", 400)


def public_settings(session: AnalysisSession) -> dict[str, Any]:
    ensure_llm(session)
    slots = []
    for row in SLOT_CATALOG:
        slot = session.llm_slots[row["id"]]
        has_user = bool((slot.get("user_api_key") or "").strip())
        has_builtin = bool(builtin_key(row["id"]))
        slots.append({
            "id": row["id"],
            "provider": row["provider"],
            "label": row["label"],
            "model": slot.get("model") or _default_model(row["id"]),
            "key_mode": slot.get("key_mode") or "builtin",
            "has_builtin_key": has_builtin,
            "has_user_key": has_user,
            "ready": slot_ready(slot),
        })
    active = session.llm_slots[session.llm_active_id]
    active_row = catalog_row(session.llm_active_id)
    return {
        "active_id": session.llm_active_id,
        "active_label": active_row["label"],
        "active_model": active.get("model") or _default_model(session.llm_active_id),
        "slots": slots,
    }


def apply_settings(session: AnalysisSession, active_id: str, updates: list[Any]) -> dict[str, Any]:
    ensure_llm(session)
    if active_id not in _VALID_IDS:
        raise AppError("Proveedor desconocido.", 400)
    for item in updates:
        sid = getattr(item, "id", None) or (item.get("id") if isinstance(item, dict) else None)
        if sid not in _VALID_IDS:
            raise AppError("Proveedor desconocido.", 400)
        slot = session.llm_slots[sid]
        model = getattr(item, "model", None)
        if model is None and isinstance(item, dict):
            model = item.get("model")
        if isinstance(model, str) and model.strip():
            slot["model"] = model.strip()
        key_mode = getattr(item, "key_mode", None)
        if key_mode is None and isinstance(item, dict):
            key_mode = item.get("key_mode")
        if key_mode in _KEY_MODES:
            slot["key_mode"] = key_mode
        api_key = getattr(item, "api_key", None)
        if api_key is None and isinstance(item, dict) and "api_key" in item:
            api_key = item.get("api_key")
        if api_key is None:
            continue
        if not isinstance(api_key, str):
            raise AppError("La clave de API no es válida.", 400)
        slot["user_api_key"] = api_key.strip()
    session.llm_active_id = active_id
    active = session.llm_slots[active_id]
    if not slot_ready(active):
        label = catalog_row(active_id)["label"]
        raise AppError(
            f"Falta la clave de API de {label}. Pégala en Ajustes o usa la del servidor.",
            400,
        )
    return public_settings(session)


def ordered_slot_ids(session: AnalysisSession) -> list[str]:
    ensure_llm(session)
    ids = [session.llm_active_id]
    for row in SLOT_CATALOG:
        if row["id"] not in ids:
            ids.append(row["id"])
    return ids
