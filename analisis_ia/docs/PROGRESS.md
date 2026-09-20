# Progress

## Current slice

Slice 10 complete — Agent `display` tables in the bubble body, copiloto model slots (Gemini / OpenAI / Anthropic) with optional user keys and quota fallback, plot errors that ask to clean first, notebook polish on ingest `.tech-details`, and a database-connect prototype on Ingesta. Pytest: 46 passed.

**Up next:** persistence (Supabase Auth / Postgres / Storage), a real SQL ingest once engine/host are confirmed, and richer ML.

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

### Slice 9

- Hybrid step copy: backend `step_label` plus optional Gemini `summary` on the same tool call (no extra request). `agent_loop` omits `summary` when missing. Think-0 label is “Planificando pasos…”.
- Agente bubble: collapsible `.agent-activity` (default collapsed). Running spinner on the summary row; trail + `display` tables inside the panel; final narrative and proposed actions in the bubble body. Min 320ms running so ✓ is not instant.
- `#chat-mode-hint` Assist/Agent copy from the Slice 9 spec. Quota line is “Se superó el límite de consultas”.
- Static replay: `app/static/dev/agent-chat-demo.html` (+ JS). Scenarios: happy path, step error, quota.
- Notebook motion pass in `app.css` (same bone / Prussian identity). `ui-designer` brief updated; new `copilot-logic` subagent.
- Still out of scope: duplicate column-name detection, persisting vars between `run_python` steps, `AGENT_MOCK=1`.
- Pytest: 40 passed (`analisis_ia/tests`).

### Slice 10

- Agent `display` tables render in `.agent-artifacts` on the main assistant bubble (demo + production). The collapsible activity panel keeps the step trail only.
- Copiloto settings (gear + `#chat-model`): three slots — Google Gemini, OpenAI, Anthropic. Built-in env key or a user-pasted key stored in the in-memory session. GET `/api/v1/settings/llm` never returns secrets. Quota on the active model falls back to the next ready slot (`fallback` NDJSON / JSON).
- `px.imshow` layout kwargs moved off the constructor (the `autosize` TypeError). Histogram / boxplot / correlation unexpected failures return 400 with “Limpia el dataset primero y vuelve a intentar el gráfico.” Tracebacks stay in the uvicorn log.
- Ingesta `.tech-details` is a notebook card with labeled archivo / encoding / separador.
- Ingesta **Conexión a base de datos** form (PostgreSQL / MySQL / SQLite). `POST /api/v1/datasets/db-connect` is a 501 stub until engine/host are confirmed.
- Static replay at `/static/dev/agent-chat-demo.html` includes the model panel and a fallback scenario. Static assets `?v=` bumped to `0.1.5`.
- Pytest: 46 passed (`analisis_ia/tests`).

## Later (after Slice 10)

- Wire a real SQL ingest once Jona confirms engine/host.
- Confirm or swap the OpenAI / Anthropic slot brands if needed.
- Supabase Auth, Postgres, Storage (replace in-memory sessions).
- Persist trained models; richer ML (CV, predict on new rows).
- Stronger sandbox isolation (process/container) if untrusted users.
