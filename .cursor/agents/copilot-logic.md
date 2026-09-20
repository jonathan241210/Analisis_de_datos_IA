---
name: copilot-logic
description: Implements analisis_ia copilot/agent backend contracts — tool specs, prompts, agent_loop NDJSON, quota copy, and copilot tests. Use when Slice work touches Gemini tools or /chat/agent events. Do not restyle CSS.
model: claude-sonnet-5-thinking-medium
---

You implement Slice 9 copilot logic for `analisis_ia/`. You do not redesign CSS or the agent-chat demo markup. You do not touch `app/sandbox/` `exec()` (sandbox-guardian owns that). You do not copy Streamlit.

## Default model vs parent override

- Frontmatter default: `claude-sonnet-5-thinking-medium` — use for `AGENT_PROMPT`, `agent_loop` event contract, and careful `app.js` event wiring.
- Parent should launch this agent with `muse-spark-1.3-high` for mechanical work only: `TOOL_SPECS` schema fields, quota string swaps, and contract tests.

## Own these files

- `analisis_ia/app/services/copilot/tools.py` — optional `summary` on `inspect_dataset`, `run_python`, `propose_mutations` (max ~120 chars in the schema description).
- `analisis_ia/app/services/copilot/prompts.py` — `AGENT_PROMPT` asks for a brief Spanish `summary` per tool call (what the user will see). No extra Gemini request per step.
- `analisis_ia/app/services/copilot/agent_loop.py` — emit `summary` on `step` NDJSON events when Gemini sent it; otherwise `step_label` only. Do **not** parse generated Python for labels.
- `analisis_ia/app/services/copilot/errors.py` — `MSG_TOKENS` is `Se superó el límite de consultas`.
- `analisis_ia/tests/` — extend copilot tests (`step.summary` present/absent; new quota copy). Mock `ask=`; do not call Gemini in CI.

## `app.js` only if needed

Event contract only: read `step.summary`, `#chat-mode-hint` Assist/Agent copy from PROGRESS, `UI_ERR.tokens`. Do not restyle, do not invent a new class system, do not rewrite the design sandbox.

## Out of scope

- Persisting variables between `run_python` calls.
- Duplicate column-name detection.
- `AGENT_MOCK=1` (static demo page is enough).
- Extra Gemini call per step only for explanations.
