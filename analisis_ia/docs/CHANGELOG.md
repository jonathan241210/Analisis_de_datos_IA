# Changelog

## 2026-09-20 (Slice 10 — tables, models, ingest)

### Added

- `.agent-artifacts` on Agente bubbles: intermediate `display` tables sit next to the final narrative, not inside the collapsible activity panel. Demo replay matches production.
- Copiloto model settings (gear): three slots (Google Gemini, OpenAI, Anthropic), built-in vs user API key, `GET`/`POST /api/v1/settings/llm`. Keys stay in the in-memory session and are never returned.
- Auto fallback when the active model hits the query/quota limit; UI toasts and updates `#chat-model`. Agent stream emits a `fallback` NDJSON event.
- Ingesta **Conexión a base de datos** form. `POST /api/v1/datasets/db-connect` returns 501 until engine/host are confirmed.
- Demo scenario “Fallback de modelo” on `/static/dev/agent-chat-demo.html`.

### Changed

- Correlation heatmaps pass `autosize` / `margin` / `height` to `update_layout` (not `px.imshow` kwargs).
- Histogram, boxplot, and correlation unexpected failures return 400 with “Limpia el dataset primero y vuelve a intentar el gráfico.” instead of a 500 body.
- `.tech-details` is a labeled notebook card (archivo, encoding, separador).
- Static assets `?v=` bumped to `0.1.5`.

### Tests

- Pytest: 52 passed (`analisis_ia/tests`), including correlation, histogram/boxplot clean errors, LLM settings redaction, assist/agent fallback, and the DB stub.

### Security

- 422 validation errors recursively redact `api_key` / `password` / `user_api_key` even when a sibling field failed.
- Unknown `analisis_session` cookies are not adopted as session ids.
- Copiloto “La mía” no longer falls back to the server key if the paste is empty.

## 2026-09-19 (Slice 9 — agent chat UX)

### Added

- Optional `summary` on agent tool calls (`inspect_dataset`, `run_python`, `propose_mutations`). `agent_loop` emits it on `step` NDJSON events; UI shows it under the backend `step_label`.
- Collapsible **activity panel** in Agente mode: “Planificando pasos…” with a running spinner, trail + intermediate tables inside the panel, final text and Aplicar actions in the bubble body. Minimum 320ms visible running state.
- Design replay at `/static/dev/agent-chat-demo.html` (happy path, step error, quota) with no Gemini calls.
- Cursor subagent `copilot-logic` for copilot/tool-loop work.

### Changed

- Quota copy is **“Se superó el límite de consultas”** (`MSG_TOKENS`, `UI_ERR.tokens`).
- Asistente / Agente `#chat-mode-hint` texts match the Slice 9 product copy.
- Notebook motion elevated in `app.css` (tabs, dropzone, toasts, activity spinner) without changing the bone / Prussian identity.
- Think-0 step label is “Planificando pasos…”. Static assets `?v=` bumped to `0.1.4`.

### Tests

- Pytest: 40 passed (`analisis_ia/tests`), including step `summary` present/absent.

## 2026-08-30 (agent JSON payloads)

### Fixed

- `json_safe` now maps `NaN` / `Inf` / pandas NA to `null` and dumps with `allow_nan=False`, so Gemini no longer rejects tool results (`400 INVALID_ARGUMENT`) on datasets with missing values.
- `inspect_dataset` head rows use the same null-safe records instead of `astype(str).to_dict()`, which left literal `NaN` on duplicate columns such as `sexo.1`.
- Function-call results are sent back to Gemini with role `user` (not `tool`). Gemini 3.x rejects `role=tool` with `400 INVALID_ARGUMENT`.
- Sandbox nested functions can use `pd`/`df` (single `exec` namespace). Agent tool payloads include a short runtime error (`TypeError: …`); the Execute API and AST rejects stay generic.

## 2026-08-28 (agent mode, in-place edit, chat errors)

### Added

- Copiloto **Agente** mode: Gemini chooses tools (`inspect_dataset`, `run_python` read-only, `propose_mutations`) in a bounded loop. `POST /api/v1/chat/agent` streams NDJSON steps; **Aplicar** on proposed mutations hits `POST /api/v1/chat/apply`. Assist mode remains the default.
- Live step trail in the chat (revisando nulos, duplicados, outliers, graficando, proponiendo limpieza, etc.).
- **Copiar** on a user bubble after the assistant has answered.

### Changed

- **Editar** opens an in-bubble editor and overwrites that user message (`replace_last`); it no longer pastes into the composer. Stopping a reply no longer copies the prompt back into the input.
- Gemini failures map to “Se acabaron los tokens” (quota / 429 / RESOURCE_EXHAUSTED) or “Error al generar respuesta”. Static assets `?v=` bumped to `0.1.3`.

### Fixed

- Chat error UI no longer always showed “La IA no responde”, ignoring the API `detail`.

## 2026-08-26 (chat stop/edit, safe errors, undo-all)

### Fixed

- Sandbox `np.select` with string choices no longer fails on NumPy 2’s integer `default=0`; the wrapper uses `default=""`.
- Duplicate **Reiniciar respuesta** on execute errors removed (retry stays on the assistant bubble only).
- Execute/chat/plot/ML failures show a short Spanish line in the UI; stack traces go to the uvicorn log (`analisis_ia` logger), not the DOM.

### Added

- Chat **Detener** (AbortController) keeps the user message; **Editar** on user bubbles resends after replacing that turn’s assistant reply.
- **Deshacer todos los cambios** (`POST /wrangling/reset` restores `df_original`). Last-step undo renamed **Deshacer último cambio**.
- Green `.is-ok` check on Copiar and async buttons (no dark disabled look).

### Changed

- Tooltips (`data-tip`) open above the control; dropzone tip removed (label already lists formats).

## 2026-08-26 (copilot execute routing / chrome)

### Changed

- Copilot **Ejecutar** no longer draws Plotly in the chat bubble. A figure switches to EDA (or ML if that tab is active), paints `#eda-plot` / `#ml-plot`, and leaves a short note plus an info toast.
- `display_df` tables stay in the chat result block; they no longer overwrite `#clean-table`. Dataset previews still refresh when execute mutates `df`.
- Copilot header shows `settings.gemini_model` instead of the specialist label; the MULTIAGENTE eyebrow is gone.
- Splitter hit area is unchanged; the vertical pill that looked like a scrollbar is removed.

### Added

- **Copiar** on copiloto code blocks (clipboard, brief “Copiado” label).
- Button loading: `.is-busy` spinner while async tools/chat run; `.is-ok` check (~700ms) on success. Copy uses the “Copiado” label instead of a spinner.

### Fixed

- EDA metrics, descriptive stats, and quality stayed empty after a dataset load: the report only ran on the tab click. `applyPreview` now calls `loadEda()`. Static assets use `?v=` so HTML/JS/CSS stay in sync.

## 2026-08-25 (fe-cols / toasts)

### Fixed

- Rename/drop feature-engineering pane uses two stacked columns so the drop picker and danger button stay aligned inside the card.

### Changed

- Removed copiloto +/− size buttons; the splitter still resizes the aside.
- Toasts: green on success, red on error, Prussian on info (e.g. nothing to undo).

## 2026-08-25 (boxplots / composer / toasts)

### Fixed

- Several boxplots are stacked (one subplot each) instead of sharing one axis.
- Rename/drop tools wrap when the tools column is narrow (`minmax(0,1fr)` + container query).
- Status toasts are larger and sit at the bottom of the tools pane (~4s), not a tiny corner pill.

### Added

- **Borrar gráfico** on EDA and ML plots.

### Changed

- Copilot textarea grows with the prompt; stacked/mobile chat is taller and uses larger type.

## 2026-08-25 (plot height / retry)

### Fixed

- Multi-histogram (and other Plotly) figures size the `#eda-plot` / `#ml-plot` card to the layout height so stacked charts stay inside the panel.

### Added

- **Reiniciar respuesta** on copiloto errors (and last reply) and on sandbox execute errors.

## 2026-08-25 (histogram names / toasts)

### Fixed

- Histogram 400 on survey headers: ingest strips padded names; lookup matches exact or stripped labels; each column is a query param (so `?` in the name is safe).
- Success toasts no longer sit on the plot or chat. They are small, bottom-left (~2s). Execute / draw-plot success is the result itself (no extra toast). Errors stay a larger corner toast.

## 2026-08-25 (chat UX)

### Added

- Chip column picker (toggle menu + chips) for every former multi-select tool.
- Floating `#toast` (ok/error, ~4s, near the triggering control when possible).
- Execute result block in the copiloto: stdout, table, Plotly figure; sandbox errors in the same block.
- Chat thinking indicator, short typewriter, code-block reveal, splitter and +/− size (persisted).

### Changed

- Histogram Draw refuses an empty column list in the client and scrolls to `#eda-plot` after `Plotly.react`.
- Assistant bubbles use ~1rem type; **Ejecutar** matches other primary buttons.
- Home page tests assert pickers/toast/splitter and histogram/execute JSON shape.

### Removed

- Static `.flash` status blocks in each section.
- Native `select[multiple]` lists and the `.plot:empty::after` overlay.

## 2026-08-25

### Added

- Histogram endpoint accepts several columns (`columns=`, subplots); `column=` still works.
- Inline `.flash` status on the section that ran the action.

### Changed

- Cast applies the same type to every selected column.
- Larger body type, buttons, and `select[multiple]`.

## 2026-08-25 (notebook)

### Added

- EDA sections matching legacy: metrics + dtypes, numeric describe, categorical explorer (`GET /eda/value-counts`), quality, viz subtabs.
- Cleaning layout: nulls/duplicates split, dedicated cast, feature-engineering subtabs (scale / encode / rename-drop).
- Light notebook chrome (bone canvas, Prussian accent, Source Serif 4 titles).

### Changed

- Wrangling UI and `apply_wrangling` only expose legacy ops (impute, drop duplicates, cast, scale, encode, rename, drop columns).
- Copilot cleaning prompt treats `str.upper` / int casts as generated pandas, not product buttons.
- `ui-designer` contract is light notebook, not dark lab.

### Removed

- Dedicated UI/service ops `upper`, `lower`, `strip`, `round`, `cast_int`.

## 2026-08-25 (viewport)

### Added

- Viewport shell (`100dvh` grid): tools scroll inside `.tools`; `#chat-form` composer is `flex-shrink: 0` at the bottom of the aside (no `100vh` chat column).
- Ingest drag-and-drop: `uploadFile()`, `.is-dragover`, CSV/TSV/XLSX/XLS only.
- Chat composer: Enter sends, Shift+Enter newline.
- `ui-designer` agent now uses `cursor-grok-4.6-xhigh` with a stricter visual contract.

### Changed

- Tabs as segmented control; primary / ghost / danger buttons; taller styled `select` / `select[multiple]`.
- Dropzone is a large dashed target; paper tables keep cream density on dark chrome.
- Responsive: ~1100px stacks chat under tools (~40vh); ~720px tabs scroll horizontally.

## 2026-08-25 (slice 1)

### Added

- `.cursor/agents/ui-designer.md` (Grok 4.6 high) for HTML/CSS work.
- FastAPI app under `analisis_ia/app/`: ingest, EDA, wrangling, ML, chat/execute.
- Product multi-agent (cleaning, EDA, ML) with Gemini; tab-aware complementary chat.
- Wrangling ops `upper` / `lower` / `strip` / `round` / `cast_int` (alumno → ALUMNO, 10.5 → 10).
- AST sandbox with timeout; tests in `analisis_ia/tests/` (12 passing).
- `requirements.txt`, `runtime.txt` (python-3.14.0), `.env.example`.
- HTML/CSS/JS UI: IBM Plex, dark lab + paper tables, tooltips.

### Changed

- Persistence for this slice is in-memory (Supabase stub only).
- Secrets live in `analisis_ia/.env`; venv is repo `.venv/`.
