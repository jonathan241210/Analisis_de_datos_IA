# Architecture

Modular monolith for `analisis_ia/`. MVC plus a service layer. FastAPI is the controller layer; HTML/CSS/JS are the views; domain and the in-memory session store are the model; business logic lives in services. The AST sandbox is the only place that may call `exec()`.

`ds_copilot/` is legacy and read-only. Do not copy Streamlit.

## Folder map

```
analisis_ia/
├── requirements.txt
├── runtime.txt              Python 3.14.0 (matches .venv)
├── .env.example             GEMINI_API_KEY + optional OpenAI/Anthropic (copy to .env)
├── docs/
├── tests/
└── app/
    ├── main.py              FastAPI, session cookie, Jinja, static
    ├── core/                Settings and AppError
    ├── api/v1/              datasets, eda, wrangling, ml, chat, settings
    ├── schemas/             Pydantic payloads
    ├── domain/              AnalysisSession, ExecutionResult
    ├── services/            ingestion, eda, wrangling, ml, copilot
    │   └── copilot/         orchestrator, Gemini client, LLM router + slots, agent loop + tools
    │       └── agents/      Product specialists (cleaning, eda, ml) — assist prompts
    ├── sandbox/             AST validate + timed exec
    ├── infra/               In-memory SessionStore; Supabase stub
    ├── templates/           index.html (module tabs + inner subtabs + right chat)
    └── static/              css/app.css (100dvh light notebook), js/app.js (DnD, subtabs, agent activity, model settings)
                             static/dev/agent-chat-demo.html — Slice 10 replay (tables in bubble, model chrome, no Gemini)
                             static/dev/proposals/ — four design editions (gallery + simulated app); not production UI
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

Right complementary chat. Toggle **Asistente | Agente**.

| Mode | Behavior |
|------|----------|
| Asistente (default) | Keyword `route_specialist` + one Gemini call. User runs code via **Ejecutar** (`POST /api/v1/chat/execute`). |
| Agente | Function calling loop (`inspect_dataset`, `run_python` read-only, `propose_mutations`). Streamed steps include optional Gemini `summary` on the same tool call (no extra round-trip). Intermediate `display` tables render in the bubble body. Mutations only after **Aplicar** (`POST /api/v1/chat/apply`). Vague prompts → quality audit + ML recs. |

Assist specialists (prompt only): cleaning, EDA, ML. Orchestrator still routes by keywords + active tab.

Chat providers: Gemini (google-genai), OpenAI and Anthropic (HTTP via httpx). `GET`/`POST /api/v1/settings/llm` selects the active slot. User keys live on the session object only. Quota → next ready slot.

`exec()` remains only in `app/sandbox/`. Agent `run_python` uses that sandbox and never writes `session.df` until the user confirms a wrangling op.

Ingesta can upload a file or show a SQL connection prototype (`POST /api/v1/datasets/db-connect` is a stub).

## Cursor subagents

legacy-extractor, sandbox-guardian, security-auditor, verifier, **ui-designer**, **copilot-logic**.

## Persistence

Local: in-memory sessions + cookie `analisis_session`. Supabase module is a stub (`supabase_configured`). Wire Auth/Storage in a later slice.

## How to run

From the repo root, using `.venv`:

```
python -m uvicorn app.main:app --app-dir analisis_ia --reload
```

Open `http://127.0.0.1:8000`. Set `GEMINI_API_KEY` in `analisis_ia/.env` for chat. Optional `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, or paste a key in Copiloto → Ajustes.
