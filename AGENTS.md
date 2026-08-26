# AGENTS.md — Project Directives v2-proyecto-refactor

## 1. Project Purpose (Scope & Non-Scope)
- **What it IS:** Asynchronous backend and custom HTML/CSS/JS UI for data analysis, data cleaning, EDA, and Machine Learning, powered by conversational AI agents and secure code execution.
- **What it IS NOT:**
  - It is NOT a massive Big Data platform (Spark/Hadoop).
  - It is NOT a real-time visualization tool (Kibana/Grafana).
  - It is NOT Streamlit (do not rebuild `st.session_state` / `st.write` UIs).
  - It is NOT an unrestricted execution environment (all AI-generated code must pass through the `ast` security sandbox).

---

## 2. Main Tech Stack
- **Language:** Python 3.14 (repo `.venv/`)
- **Core Framework:** FastAPI + Pydantic V2
- **Presentation:** HTML + CSS + JS (Jinja under `analisis_ia/app/templates/`; Plotly.js)
- **Database, Auth & Storage:** In-memory sessions now; Supabase later
- **Secrets file:** `analisis_ia/.env` (see `.env.example`)
- **Main AI Model:** Google Gemini API + `ast` Sandbox
- **Data Processing:** Pandas / NumPy / Scikit-learn

---

## 3. Architecture
- Target app lives in `analisis_ia/` (modular monolith: MVC + services + isolated sandbox).
- Folder map, MVC mapping, and agent boundaries: `analisis_ia/docs/ARCHITECTURE.md`.
- Product chat uses an orchestrator plus specialists (cleaning, EDA, ML). All generated code still goes through the sandbox.

---

## 4. Modification Rules
- The legacy project folder (`ds_copilot/` or old code) is **strictly read-only**.
- Extract business logic and the `ast` sandbox, but **NEVER** copy code coupled to the old Streamlit interface (`st.session_state`, `st.write`, etc.).

---

## 5. Workflow, Skills, and Cursor Subagents
- Apply skills in `.cursor/skills/` (including `analisis-ia-docs` after a closed slice).
- Delegate to project subagents in `.cursor/agents/`:
  - `legacy-extractor` — port contracts from `ds_copilot/` (read-only)
  - `sandbox-guardian` — AST / `exec` / import whitelist (read-only)
  - `security-auditor` — JWT, RLS, uploads, secrets (read-only)
  - `verifier` — confirm claimed work actually works
  - `ui-designer` — distinctive HTML/CSS/JS (no generic SaaS palette)
- Code decisions follow those skills. Do not clone Cursor built-ins (`explore`, `bash`, `browser`).

---

## 6. Security Restrictions
- Do NOT execute `exec()` code blocks outside the secure environment validated by `ast` (`analisis_ia/app/sandbox/`).
- Do NOT import dangerous modules (`os`, `sys`, `subprocess`) in AI-generated calls.
- Do NOT expose credentials or API keys in the source code (use `.env`).

---

## 7. Domain Context
- The user uploads datasets (CSV/Excel/TSV) for EDA, wrangling, and Machine Learning.
- Gemini does not operate on the full dataset: metadata and samples only; the backend runs validated code on the active DataFrame.
- In-app agents (orchestrator, cleaning, EDA, ML) are product runtime. Cursor subagents are for development only.

---

## 8. What I Expect in Responses
- **Chat:** short Spanish summary of what changed, in which file, and why.
- **Docs and agent/skill files:** English only.

---

## 9. Documentation Protocol
After each **closed slice** (not every tiny edit), update English docs in `analisis_ia/docs/` via skill `analisis-ia-docs`:
- **`PROGRESS.md`:** Current status (done, blocked, next).
- **`CHANGELOG.md`:** Technical changelog.
- **`ARCHITECTURE.md`:** Module map — only when structure or boundaries change.
