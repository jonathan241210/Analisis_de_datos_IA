# Feature gaps (not scheduled)

Compared with Julius AI, Hex notebooks, and similar analyst copilots (Observable / spreadsheet-AI tools). This list is research for Jona — **none of it is implemented** in this slice. Design proposals under `app/static/dev/proposals/` only restyle the existing flow.

## Already in analisis_ia (Slice 10)

- CSV / TSV / Excel ingest with encoding and separator detection
- EDA: shape, dtypes, numeric describe, categorical summary, quality, histogram / boxplot / correlation
- Wrangling: impute, drop duplicates, cast, scale, encode, rename, drop columns, undo (15), export CSV
- ML: classification / regression, K-Means (elbow), DBSCAN, PCA — in-session only
- Copilot Assist + Agent (AST sandbox, propose-then-apply)
- Gemini / OpenAI / Anthropic slots with quota fallback
- Database-connect **form** (`POST /datasets/db-connect` is 501)

## Missing (do not build until chosen)

1. **Live sources** — real SQL (Postgres / MySQL / warehouses such as BigQuery, Snowflake), Google Sheets, Drive. The DB form is a stub.
2. **More file types** — JSON, Parquet, tabular PDF, URL ingest, bundled sample datasets (Julius accepts PDF and Sheets).
3. **Richer viz** — scatter, time series, violin, pairplot, maps. Today: hist, box, corr only.
4. **Inferential stats** — t-test, chi-square, ANOVA, normality tests (descriptives only today).
5. **Outlier treatment and joins** — agent can *detect* IQR outliers; there is no winsorize/clip op, and no merge of several tables.
6. **Reproducible pipeline** — export the wrangling history as a re-runnable script or notebook (Julius notebooks / Hex cells).
7. **Product-grade ML** — cross-validation, predict on new rows, persist models, forecasting. Training dies with the in-memory session.
8. **Sandbox memory** — persist `run_python` variables across agent steps; duplicate column-name handling; PDF / slide reports.
9. **Accounts** — Auth, projects, collaboration, scheduled runs. Sessions are still in-memory cookies.
10. **Explainability** — feature importance / SHAP, a column dictionary, and a production dark theme (Observatorio is a proposal only).

Pick items for the next product slice; the design gallery is independent of this list.
