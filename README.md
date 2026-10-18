# analisis_ia

Asynchronous data-analysis web app: upload CSV/TSV/Excel, explore and clean data, run EDA and ML, and use a tab-aware AI copilot. AI-generated Python runs only inside an AST-validated sandbox—not in Streamlit and not as unrestricted `exec()`.

The active product lives in **`analisis_ia/`**. The **`ds_copilot/`** folder is a legacy Streamlit prototype kept **read-only** for reference when porting business logic.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.14 (see `analisis_ia/runtime.txt`) |
| API | [FastAPI](https://fastapi.tiangolo.com/) + Pydantic v2 |
| UI | Jinja2 templates, vanilla HTML/CSS/JS, [Plotly.js](https://plotly.com/javascript/) |
| Data | pandas, NumPy, scikit-learn, XGBoost |
| AI | Google Gemini API (`google-genai`) |
| Execution | Custom AST sandbox (`analisis_ia/app/sandbox/`) |
| Tests | pytest, httpx |
| Persistence (current) | In-memory sessions + cookie; Supabase planned |

Secrets: copy `analisis_ia/.env.example` to `analisis_ia/.env` (never commit `.env`).

---

## Repository layout

```
agente/
├── AGENTS.md                 # Cursor / agent directives for this repo
├── README.md                 # This file
├── .cursor/
│   ├── agents/               # Project subagents (verifier, ui-designer, …)
│   └── skills/
│       └── analisis-ia-docs/ # Project skill (tracked); other skills are local-only
├── analisis_ia/              # Active application (see below)
└── ds_copilot/               # Legacy Streamlit app — read-only, do not extend
```

### `analisis_ia/` (application)

Modular monolith: MVC + services + isolated sandbox. Details: [`analisis_ia/docs/ARCHITECTURE.md`](analisis_ia/docs/ARCHITECTURE.md).

```
analisis_ia/
├── requirements.txt
├── runtime.txt
├── .env.example
├── docs/                     # PROGRESS, CHANGELOG, ARCHITECTURE
├── tests/
└── app/
    ├── main.py               # FastAPI, session cookie, Jinja, static files
    ├── core/                 # Settings, AppError
    ├── api/v1/               # datasets, eda, wrangling, ml, chat
    ├── schemas/              # Pydantic request/response models
    ├── domain/               # AnalysisSession, ExecutionResult
    ├── services/             # ingestion, eda, wrangling, ml, copilot
    │   └── copilot/          # Orchestrator, Gemini client, prompts
    │       └── agents/       # In-app specialists: cleaning, eda, ml
    ├── sandbox/              # AST validation + timed exec (only place for exec())
    ├── infra/                # In-memory SessionStore (Supabase stub later)
    ├── templates/            # index.html — tabs + chat aside
    └── static/               # css/app.css, js/app.js
```

**Product flow:** four tool tabs (Ingest, EDA, Cleaning, ML) plus a complementary chat aside. The copilot suggests pandas/Plotly code; the user runs **Ejecutar**, which calls `POST /api/v1/chat/execute` through the sandbox.

---

## Quick start

From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r analisis_ia/requirements.txt
copy analisis_ia\.env.example analisis_ia\.env   # set GEMINI_API_KEY
python -m uvicorn app.main:app --app-dir analisis_ia --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Chat needs a valid `GEMINI_API_KEY`; ingest, EDA, wrangling, and ML tools work without it.

Run tests:

```bash
cd analisis_ia
python -m pytest tests -q
```

---

## `AGENTS.md`

[`AGENTS.md`](AGENTS.md) is the **project contract for AI coding agents** (e.g. Cursor). It defines:

- What this repo **is** and **is not** (no Streamlit UI, no Big Data platform, sandbox-only execution)
- Stack, architecture pointer, and modification rules (`ds_copilot/` is read-only)
- Security constraints (no dangerous imports in generated code, secrets in `.env`)
- Which **Cursor subagents** and **skills** to use during development
- Documentation protocol (`analisis_ia/docs/` after each closed slice)

Agents and humans should read it before large changes.

---

## Cursor skills (optional)

This repo ships a small **project-specific** skill under `.cursor/skills/analisis-ia-docs/` and subagents under `.cursor/agents/`. Those are meant to be **committed**.

General-purpose skills (FastAPI, testing, security, etc.) can be installed locally with the [agent-skills-cli](https://www.npmjs.com/package/agent-skills-cli) and the [**claude-skills**](https://github.com/Jeffallan/claude-skills) collection:

```bash
npx agent-skills-cli@latest add @Jeffallan/claude-skills
```

That installs skills into `.cursor/skills/`. They are **gitignored** by default (see `.gitignore`) so each developer reinstalls them; only `analisis-ia-docs` stays in version control.

**Reference:** [Jeffallan/claude-skills on GitHub](https://github.com/Jeffallan/claude-skills/tree/main) — 67 specialized skills for full-stack development (MIT license).

---

## Documentation

| Document | Purpose |
|----------|---------|
| [`analisis_ia/docs/ARCHITECTURE.md`](analisis_ia/docs/ARCHITECTURE.md) | Module map, MVC, in-app agents |
| [`analisis_ia/docs/PROGRESS.md`](analisis_ia/docs/PROGRESS.md) | Current slice status |
| [`analisis_ia/docs/CHANGELOG.md`](analisis_ia/docs/CHANGELOG.md) | Technical changelog |

---

## License

No root license file yet. Legacy code in `ds_copilot/` and third-party skills follow their respective upstream licenses.
