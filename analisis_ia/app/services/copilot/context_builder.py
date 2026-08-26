import re

import pandas as pd

from app.core.config import settings
from app.services.dataframe_ops import categorical_columns, numeric_columns

KEYWORDS_CLEANING = ["nulo", "nulos", "nan", "faltante", "limpieza", "limpiar", "duplicad", "mayúsc", "minusc", "redonde"]
KEYWORDS_CORRELATION = ["correlaci", "relaci", "patrón", "patron", "asociaci"]
KEYWORDS_OUTLIERS = ["outlier", "atípic", "atipic", "anomal", "iqr", "rango intercuart"]
KEYWORDS_ML = ["modelo", "cluster", "clasificaci", "regresi", "predic", "entrenar", "machine learning", "ml"]
KEYWORDS_PLOTTING = ["gráfic", "grafic", "plot", "histograma", "boxplot", "visualiz", "chart"]


def detect_intents(query: str) -> set[str]:
    q = query.lower()
    intents: set[str] = set()
    if any(k in q for k in KEYWORDS_CLEANING):
        intents.add("cleaning")
    if any(k in q for k in KEYWORDS_CORRELATION):
        intents.add("correlation")
    if any(k in q for k in KEYWORDS_OUTLIERS):
        intents.add("outliers")
    if any(k in q for k in KEYWORDS_ML):
        intents.add("ml")
    if any(k in q for k in KEYWORDS_PLOTTING):
        intents.add("plotting")
    return intents


def route_specialist(query: str, active_tab: str) -> str:
    intents = detect_intents(query)
    if "ml" in intents:
        return "ml"
    if "cleaning" in intents:
        return "cleaning"
    if "correlation" in intents or "outliers" in intents or "plotting" in intents:
        return "eda"
    tab = (active_tab or "eda").lower()
    if tab in {"cleaning", "wrangling", "limpieza"}:
        return "cleaning"
    if tab in {"ml", "machine_learning"}:
        return "ml"
    return "eda"


def _exact_schema_block(df: pd.DataFrame) -> str:
    columns = df.columns.tolist()
    truncated = len(columns) > settings.max_columns_in_metadata
    listed = columns[: settings.max_columns_in_metadata] if truncated else columns
    schema_lines = [f"  - {repr(c)} → {t}" for c, t in zip(listed, df[listed].dtypes.astype(str))]
    header = (
        "### ESQUEMA EXACTO DEL DATAFRAME (usa estos nombres LITERALMENTE)\n"
        f"- Dimensiones: {df.shape[0]} filas × {df.shape[1]} columnas\n"
        + (f" — mostrando {settings.max_columns_in_metadata} de {len(columns)}:" if truncated else ":")
        + "\n" + "\n".join(schema_lines)
    )
    head_sample = "\n**Muestra real df.head(2):**\n" + df.head(2).to_markdown(index=False)
    return header + "\n" + head_sample


def build_context(df: pd.DataFrame, user_query: str) -> str:
    lines = [_exact_schema_block(df)]
    if len(df) > settings.n_head_rows:
        sample_n = min(settings.n_sample_rows, len(df))
        lines.append(
            "\n**Muestra aleatoria adicional:**\n"
            + df.sample(n=sample_n, random_state=42).to_markdown(index=False)
        )
    null_counts = df.isnull().sum()
    null_pct = (null_counts / len(df) * 100).round(1) if len(df) else null_counts
    null_summary = ", ".join(
        f"{c}: {n} ({p}%)" for c, n, p in zip(df.columns, null_counts, null_pct) if n > 0
    )
    lines.append(f"\n- Nulos por columna: {null_summary or 'ninguna columna tiene nulos'}")

    num_cols = numeric_columns(df)
    if num_cols:
        lines.append("\n**df.describe() (numéricas):**\n" + df[num_cols].describe().to_markdown())
    cat_cols = categorical_columns(df)
    if cat_cols:
        top_vals = []
        for c in cat_cols[:8]:
            vc = df[c].value_counts().head(settings.n_top_categories)
            nuniq = int(df[c].nunique(dropna=False))
            sample = ", ".join(f"{i}={v}" for i, v in vc.items())
            top_vals.append(f"  - {c}: uniques={nuniq}, top: {sample}")
        lines.append("\n**Top valores categóricos:**\n" + "\n".join(top_vals))

    intents = detect_intents(user_query)
    if "cleaning" in intents:
        lines.append(f"\n### Extra limpieza\nDuplicados: {int(df.duplicated().sum())}")
    if "correlation" in intents and len(num_cols) >= 2:
        lines.append("\n### Extra correlaciones\n" + df[num_cols].corr(numeric_only=True).round(2).to_markdown())
    if "outliers" in intents:
        rows = []
        for c in num_cols:
            q1, q3 = df[c].quantile(0.25), df[c].quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            n_out = int(((df[c] < lower) | (df[c] > upper)).sum())
            rows.append(f"  - {c}: outliers≈{n_out}")
        lines.append("\n### Extra outliers\n" + "\n".join(rows))
    if "ml" in intents:
        rows = [f"  - {c}: min={df[c].min():.2f}, max={df[c].max():.2f}" for c in num_cols]
        lines.append("\n### Extra ML\n" + "\n".join(rows))
    if "plotting" in intents:
        mentioned = [c for c in df.columns if re.search(rf"\b{re.escape(str(c))}\b", user_query, re.IGNORECASE)]
        cols = mentioned if mentioned else df.columns.tolist()[:5]
        lines.append(f"\n### Extra gráficos\nColumnas: {cols}")
    return "\n".join(lines)
