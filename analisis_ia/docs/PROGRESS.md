# Progress

## Current slice

Slice 5 complete — chip column pickers, floating toasts, execute results in chat, resizable copiloto.

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

## Blocked

- Chat replies need a real `GEMINI_API_KEY` in `analisis_ia/.env`. Static tools work without it.

## Next (product)

- Supabase Auth, Postgres, Storage (replace in-memory sessions).
- Persist trained models; richer ML (CV, predict on new rows).
- Stronger sandbox isolation (process/container) if untrusted users.
