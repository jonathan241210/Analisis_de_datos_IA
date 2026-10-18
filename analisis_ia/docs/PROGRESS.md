# Progress

## Current slice

Slice 9 complete — Agent chat UX (hybrid `summary` + activity panel) and notebook motion pass. Design replay at `/static/dev/agent-chat-demo.html`; production `app.js` paints the same panel. Quota copy is “Se superó el límite de consultas”. Pytest: 40 passed.

**Up next:** Slice 10 — listed below. Chat UX changes are prototyped on `/static/dev/agent-chat-demo.html` before production `app.js`.

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

## Next (Slice 10 — planned)

Chat items **1–2** iterate on the demo page first, then merge into production. Tools/ingest items **3–5** can land on the live app.

### 1. Agent `display` tables in the bubble (not inside the activity panel)

Today intermediate `.exec-result` tables sit in `.agent-activity-body` (the collapsible trail). Keep the step list + summaries in that panel. Move **tables / query results** into the main `.bubble.assistant.agent-run` body, next to the final narrative (they are part of what the user should see, not only activity).

- First: `app/static/dev/agent-chat-demo.html` (+ `agent-chat-demo.js`).
- Then: the same layout in production `app.js`.

### 2. Model picker + own API key (settings)

`#chat-model` (or a settings control next to it) must choose among providers, not only Gemini.

- **Three slots for now** (Gemini + two TBD; Jona will confirm which). Built-in vs “use my key”.
- Settings: floating panel or gear. User can paste an API key in the UI and pick that model for chat.
- **Auto fallback:** if the current model hits the query/quota limit, switch to the next configured model.
- Secrets stay out of source; do not log keys. Demo the picker chrome on `agent-chat-demo.html` before wiring real providers.

### 3. Plot / correlation errors → clean data first

When histogram, boxplot, correlation, or similar viz fails (example already seen: `GET /eda/correlation` → `TypeError: imshow() got an unexpected keyword argument 'autosize'`), the UI must not dump a 500. Show a short Spanish line: clean the dataset first, then retry the chart. Keep the traceback in the server log.

### 4. Ingest `.tech-details` visual polish

`details.tech-details` (file name, encoding, separator) looks too bare. Restyle it in the notebook identity (same palette; not a new brand).

### 5. Database connection (ingest)

Add a database connection area: either a block on the **Ingesta** panel or a dedicated subsection/tab. Prototype UX on the live ingest screen (not the chat demo). Engine/host details TBD with Jona.

## Later (after Slice 10)

- Supabase Auth, Postgres, Storage (replace in-memory sessions).
- Persist trained models; richer ML (CV, predict on new rows).
- Stronger sandbox isolation (process/container) if untrusted users.
