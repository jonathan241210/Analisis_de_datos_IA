from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from pandas import DataFrame

from app.core.config import settings
from app.sandbox.extract import extract_python_code
from app.services.copilot.gemini_client import ModelTurn, generate_with_tools
from app.services.copilot.prompts import AGENT_PROMPT
from app.services.copilot.tools import dispatch_tool, step_label

AskFn = Callable[[list[dict[str, Any]]], Awaitable[ModelTurn]]


def _seed_contents(user_query: str, active_tab: str, history: list[dict[str, str]]) -> list[dict[str, Any]]:
    hist_lines = []
    for msg in (history or [])[-6:]:
        hist_lines.append(f"{msg.get('role', 'user')}: {msg.get('content', '')}")
    hist_block = "\n".join(hist_lines)
    text = f"Pestaña activa: {active_tab}\n"
    if hist_block:
        text += f"Historial reciente:\n{hist_block}\n"
    text += f"Solicitud del usuario:\n{user_query}\n"
    return [{"role": "user", "text": text}]


async def _default_ask(contents: list[dict[str, Any]]) -> ModelTurn:
    return await generate_with_tools(AGENT_PROMPT, contents)


def _tool_summary(args: dict[str, Any], limit: int = 120) -> str:
    raw = args.get("summary")
    if not isinstance(raw, str):
        return ""
    text = raw.strip()
    if not text:
        return ""
    return text[:limit]


async def run_agent_loop(
    df: DataFrame,
    user_query: str,
    history: list[dict[str, str]],
    active_tab: str,
    ask: AskFn | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield NDJSON-ready events: step, fig, display, final, error."""
    ask_fn = ask or _default_ask
    contents = _seed_contents(user_query, active_tab, history)
    proposed: list[dict[str, Any]] = []
    step_i = 0
    last_text = ""

    yield {"type": "step", "id": "think-0", "label": "Planificando pasos…", "status": "running"}

    for _ in range(max(1, settings.agent_max_steps)):
        turn = await ask_fn(contents)
        last_text = turn.text or last_text
        if not turn.calls:
            yield {"type": "step", "id": "think-0", "label": "Planificando pasos…", "status": "done"}
            yield {
                "type": "final",
                "content": last_text or "Listo.",
                "code_blocks": extract_python_code(last_text or ""),
                "proposed_actions": proposed,
            }
            return

        yield {"type": "step", "id": "think-0", "label": "Planificando pasos…", "status": "done"}

        model_item: dict[str, Any] = {
            "role": "model",
            "text": turn.text or "",
            "calls": turn.calls,
            "raw": turn.raw_model_content,
        }
        contents.append(model_item)
        tool_results: list[dict[str, Any]] = []
        for call in turn.calls:
            step_i += 1
            sid = f"t{step_i}"
            name = str(call.get("name") or "")
            args = call.get("args") or {}
            label = step_label(name, args)
            summary = _tool_summary(args)
            running_step: dict[str, Any] = {"type": "step", "id": sid, "label": label, "status": "running"}
            if summary:
                running_step["summary"] = summary
            yield running_step
            payload, extra = dispatch_tool(df, name, args)
            if extra.get("proposed_actions"):
                proposed.extend(extra["proposed_actions"])
            if extra.get("fig"):
                yield {"type": "fig", "fig": extra["fig"]}
            if extra.get("display"):
                yield {"type": "display", "display": extra["display"]}
            ok = "error" not in payload or payload.get("success") is True
            if name == "run_python":
                ok = bool(payload.get("success"))
            done_step: dict[str, Any] = {
                "type": "step",
                "id": sid,
                "label": label.rstrip("…"),
                "status": "done" if ok or name == "propose_mutations" else "error",
            }
            if summary:
                done_step["summary"] = summary
            yield done_step
            tool_results.append({
                "name": name,
                "call_id": str(call.get("call_id") or ""),
                "response": {"result": payload},
            })
        contents.append({"role": "tool", "results": tool_results})
        yield {"type": "step", "id": "think-0", "label": "Planificando pasos…", "status": "running"}

    yield {"type": "step", "id": "think-0", "label": "Planificando pasos…", "status": "done"}
    yield {
        "type": "final",
        "content": last_text or "Alcancé el límite de pasos. Revisa el avance y vuelve a preguntar si hace falta.",
        "code_blocks": extract_python_code(last_text or ""),
        "proposed_actions": proposed,
    }
