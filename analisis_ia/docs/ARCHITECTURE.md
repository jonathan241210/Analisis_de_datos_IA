# Architecture

Modular monolith for `analisis_ia/`. MVC plus a service layer. FastAPI is the controller layer; HTML/CSS/JS are the views; domain and the in-memory session store are the model; business logic lives in services. The AST sandbox is the only place that may call `exec()`.

`ds_copilot/` is legacy and read-only. Do not copy Streamlit.

## Folder map

```
analisis_ia/
├── requirements.txt
├── runtime.txt              Python 3.14.0 (matches .venv)
├── .env.example             GEMINI_API_KEY (copy to .env)
├── docs/
├── tests/
└── app/
    ├── main.py              FastAPI, session cookie, Jinja, static
    ├── core/                Settings and AppError
    ├── api/v1/              datasets, eda, wrangling, ml, chat
    ├── schemas/             Pydantic payloads
    ├── domain/              AnalysisSession, ExecutionResult
    ├── services/            ingestion, eda, wrangling, ml, copilot
    │   └── copilot/agents/  Product specialists (cleaning, eda, ml)
    ├── sandbox/             AST validate + timed exec
    ├── infra/               In-memory SessionStore; Supabase stub
    ├── templates/           index.html (module tabs + inner subtabs + right chat)
    └── static/              css/app.css (100dvh light notebook), js/app.js (DnD, subtabs)
```

### MVC mapping

| MVC role | Location |
|----------|----------|
| Controller | `app/api/v1/` |
| View | `app/templates/`, `app/static/`, JSON schemas |
| Model | `app/domain/` + `app/infra/session_store.py` |
| Service | `app/services/` |
| Security boundary | `app/sandbox/` |

## Product agents (in-app)

Right complementary chat. Active tab biases routing; the orchestrator can still hand off.

| Agent | Responsibility |
|-------|----------------|
| Orchestrator | `route_specialist` + Gemini call |
| Cleaning | Nulls, dups, type cast, scale, encode, rename/drop |
| EDA | Metrics, quality, charts |
| ML | Supervised / unsupervised |

Chat is two-step: generate code, then **Ejecutar** hits `/api/v1/chat/execute` (sandbox).

## Cursor subagents

legacy-extractor, sandbox-guardian, security-auditor, verifier, **ui-designer**.

## Persistence

Local: in-memory sessions + cookie `analisis_session`. Supabase module is a stub (`supabase_configured`). Wire Auth/Storage in a later slice.

## How to run

From the repo root, using `.venv`:

```
python -m uvicorn app.main:app --app-dir analisis_ia --reload
```

Open `http://127.0.0.1:8000`. Set `GEMINI_API_KEY` in `analisis_ia/.env` for chat.
