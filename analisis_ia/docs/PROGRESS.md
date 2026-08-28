# Progress

## Current slice

Slice 7 complete — np.select sandbox compat, one retry per bubble, green copy/ok, chat stop/edit, user-safe errors (logs in terminal), undo-all + tooltips above.

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

## Next (product)

- **Agent mode (tools + loop):** optional Copiloto mode, not a one-shot LLM and not a fixed pipeline. Gemini chooses tools (`inspect_dataset`, `run_python` read-only, wrangling ops) in a bounded loop: act, observe stdout/preview/error, decide the next step. Vague prompts default to a full quality audit (nulls, duplicates, outliers, types) plus ML recommendations (useful columns, task type). Mutations (impute, drop, encode, drop duplicates) only after explicit user confirm. The chat shows a brief live step trail (e.g. “Revisando nulos…”, “Buscando outliers…”, “Graficando…”) so the user sees what the agent is doing. Assist mode stays the default (one-shot chat + manual Ejecutar).
- **Chat edit/copy UX:** Editar must overwrite the sent user bubble in place when the user stopped the reply (no copy-into-composer). If the model already answered, hide Editar and show Copiar on that user message.
- **Chat error copy:** quota/token exhaustion → explicit Spanish line that tokens ran out; any other Gemini failure → “Error al generar respuesta”. Do not leak raw API text.
- Supabase Auth, Postgres, Storage (replace in-memory sessions).
- Persist trained models; richer ML (CV, predict on new rows).
- Stronger sandbox isolation (process/container) if untrusted users.
