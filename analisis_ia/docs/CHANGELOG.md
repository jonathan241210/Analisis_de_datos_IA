# Changelog

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
