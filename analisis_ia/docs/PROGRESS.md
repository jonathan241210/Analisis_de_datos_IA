# Progress

## Current slice

Slice 8 complete — Copiloto **Agente** mode (Gemini tools + bounded loop + live step trail; mutations need confirm), in-place **Editar** / **Copiar** on user bubbles, token vs generic chat errors.

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

## Next (product)

- Supabase Auth, Postgres, Storage (replace in-memory sessions).
- Persist trained models; richer ML (CV, predict on new rows).
- Stronger sandbox isolation (process/container) if untrusted users.
