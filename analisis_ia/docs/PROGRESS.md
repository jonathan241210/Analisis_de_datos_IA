# Progress

## Current slice

Slice 8 complete — Copiloto **Agente** mode (tools loop, NDJSON steps, mutation confirm). Post–Slice 8 fixes: strict JSON tool payloads, Gemini `user` role for function results, sandbox single namespace + agent runtime `detail`.

**Up next:** Slice 9 — Agent chat UX (documented below; not started).

## Completed

### Slice 1

- FastAPI app: ingest, EDA, wrangling, ML, complementary chat, AST sandbox.
- Pytest: originally 12 tests.

### Slice 2

- Viewport shell (`100dvh`); composer pinned; drag-and-drop ingest.

### Slice 3

- Light notebook palette (bone / ink / Prussian). Dark lab amber/teal removed.
- Tools grouped like the legacy app: EDA four sections; cleaning nulls/cast/feature-engineering; ML supervised vs unsupervised subtabs.
- Removed first-class `upper` / `lower` / `strip` / `round` / `cast_int` (those were explanation examples). Copilot can still generate pandas for them.

### Slice 4

- Histogram and cast accept several columns on the API.
- Larger labels, buttons, and type.

### Slice 5

- Native `select[multiple]` replaced by a chip picker (checkbox menu, click to toggle) on histogram, boxplot, impute, cast, scale, encode, drop, and ML feature lists.
- Histogram Draw with zero columns shows a floating error toast instead of a silent 400; Plotly `react` is try/caught and `#eda-plot` scrolls into view. The empty-plot CSS overlay was removed so it cannot cover a figure.
- Section `.flash` blocks removed. One `#toast` (fixed, ok/error, ~4s) for tools and chat.
- `POST /chat/execute` still updates tab previews when `df` mutates; stdout, display/preview table, and Plotly `fig` also render in a result block under **Ejecutar**. Sandbox errors show in that block.
- Copilot: “Pensando…” while waiting, short typewriter + code reveal (skipped if `prefers-reduced-motion`), larger bubbles, splitter +/− with `localStorage` (width on desktop, height under ~1100px). Composer stays `flex-shrink: 0`.
- Pytest: 14 passed (`analisis_ia/tests`).

### Slice 6

- Execute figures redirect to the EDA or ML visualization slot; they are not duplicated in chat.
- Query `display_df` tables stay in the chat; Limpieza’s dataset table is only updated when `df` mutates.
- Copiar on code blocks; async buttons show a spinner then a short success check.
- Aside: Gemini model name from settings; no MULTIAGENTE / specialist line. Splitter is an invisible drag handle.
- EDA report loads when a dataset preview is applied (not only on tab click), so metrics/quality are filled before opening the tab. Static CSS/JS are cache-busted (`?v=`).
- Pytest: 19 passed (`analisis_ia/tests`).

### Slice 7

- Sandbox `np.select` string choices; execute errors are generic in the UI; technical detail is logged.
- Chat: Detener (client abort) and Editar on user messages; a single Reiniciar respuesta per assistant bubble.
- Limpieza: undo last vs reset all; tooltips above the buttons; dropzone has no duplicate tip.
- Pytest: 20 passed (`analisis_ia/tests`).

### Slice 8

- Copiloto toggle **Asistente | Agente**. Assist stays one-shot + manual Ejecutar. Agent mode: Gemini function calling in a bounded loop (`inspect_dataset`, `run_python` read-only, `propose_mutations`). Vague prompts default to a quality audit plus ML recommendations. Mutations apply only after the user confirms (`POST /api/v1/chat/apply`). NDJSON stream paints a live step trail (nulos, duplicados, outliers, graficando, etc.).
- **Editar** overwrites the sent user bubble in place when the reply was stopped (no copy-into-composer). After the model answers, that user bubble shows **Copiar** instead of Editar. Abort no longer refills the composer.
- Chat errors: quota/token exhaustion → “Se acabaron los tokens”; any other Gemini failure → “Error al generar respuesta”. Raw API text stays in the server log.
- Pytest: 32 passed (`analisis_ia/tests`).
- Agent tool results (`json_safe` / `inspect_dataset` head) convert pandas/NumPy `NaN` and infinities to JSON `null`. Function responses are sent with role `user` so Gemini 3.x accepts the next turn.
- Sandbox `exec` uses one namespace so nested functions see `pd`/`df`. Agent `run_python` gets `TypeError: …` (no traceback); **Ejecutar** still shows the generic line. AST rejections stay generic for both.

## Next (Slice 9 — Agent chat UX + design replay)

**Goal:** Clearer Agent-mode chat without extra Gemini round-trips per step. Iterate layout on a mock replay page before wiring production `/chat/agent`.

### Hybrid step copy (backend + Gemini)

| Layer | Owner | Role |
|-------|--------|------|
| Step status label | Backend (`step_label`, fixed enums) | Short generic line: “Revisando el dataset…”, “Ejecutando análisis…”, spinner while running |
| Brief “why” line | Gemini (same tool call, no extra request) | Optional `summary` string on each function call (1 sentence, Spanish, user-facing) |
| Final answer | Gemini (`final` event) | Full narrative after the loop |

**Backend changes (planned):**

- Add optional `summary` to `TOOL_SPECS` for `inspect_dataset`, `run_python`, `propose_mutations` (max ~120 chars in schema description).
- Extend `AGENT_PROMPT`: ask for a brief `summary` per tool call explaining what the user will see.
- `agent_loop`: emit `summary` on `step` NDJSON events when present; fall back to `step_label` only.
- Do **not** parse generated Python for labels (keep backend generic).

**UI changes (planned):**

- Collapsible **activity panel** inside the agent bubble (default: collapsed summary row).
  - Summary row while waiting on Gemini: **“Planificando pasos…”** + visible running animation (not only `✓`).
  - Expanded: step trail with `is-running` spinner; intermediate artifacts live here.
- **Intermediate vs final:** `display` tables and small previews inside the panel; **final** text + proposed actions stay in the main bubble body (typewriter).
- Fix perceived “instant ✓”: ensure running state is visible (CSS animation, optional min display time for fast tools).

### Chat copy (`#chat-mode-hint`, quota error)

**Assist hint (planned):**

> Recomendado para tareas concretas: pide código y ejecútalo con **Ejecutar**. Las tablas aparecen en el chat; las gráficas en Visualización (EDA o ML).

**Agent hint (planned):**

> Recomendado para diagnosticar el dataset (calidad, patrones, siguientes pasos). Usa más consultas a la IA; el límite diario puede agotarse antes. Los cambios al dataset piden confirmación.

**Quota message (planned):** replace “Se acabaron los tokens” with **“Se superó el límite de consultas”** in `app/services/copilot/errors.py` (`MSG_TOKENS`), `app/static/js/app.js` (`UI_ERR.tokens`), and tests.

### Design sandbox (no Gemini)

Static replay for layout/CSS iteration without burning API quota:

- `analisis_ia/app/static/dev/agent-chat-demo.html` (+ JS) reusing `app.css` chat styles.
- Replays canned NDJSON sequences (`step`, `display`, `fig`, `final`, `error`) with artificial delays.
- Scenarios: happy path (inspect → table → final), step error, quota error.
- Optional later: `AGENT_MOCK=1` on `/chat/agent` — prefer static page first.
- Merge into production `app.js` only after visual sign-off.

### Out of scope (Slice 9)

- Duplicate column-name detection in EDA ingest.
- Persisting variables between `run_python` calls across steps (`df_c` in a later step).
- Extra Gemini call per step only for explanations.

### Files (expected touch)

- `app/services/copilot/tools.py` — `summary` in tool specs
- `app/services/copilot/prompts.py` — `AGENT_PROMPT`
- `app/services/copilot/agent_loop.py` — `step.summary` in events
- `app/static/js/app.js`, `app/static/css/app.css` — activity panel, hints
- `app/templates/index.html` — default hint text if not JS-only
- `app/services/copilot/errors.py`, tests — quota copy
- `app/static/dev/agent-chat-demo.html` — design replay

## Next (product, after Slice 9)

- Supabase Auth, Postgres, Storage (replace in-memory sessions).
- Persist trained models; richer ML (CV, predict on new rows).
- Stronger sandbox isolation (process/container) if untrusted users.
