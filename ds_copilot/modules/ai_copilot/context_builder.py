"""
modules/ai_copilot/context_builder.py
Construye el payload de metadata que se envía a la IA en cada mensaje.

REGLA DE ORO: nunca se envía el dataset completo, solo metadata + muestras
representativas + bloques de contexto adicionales SOLO si la consulta lo requiere.
"""
import re
import pandas as pd

from config import N_HEAD_ROWS, N_SAMPLE_ROWS, N_TOP_CATEGORIES, MAX_COLUMNS_IN_METADATA
from utils.helpers import numeric_columns, categorical_columns


# --- Palabras clave para el enrutamiento de contexto adaptativo ---
KEYWORDS_CLEANING = ["nulo", "nulos", "nan", "faltante", "limpieza", "limpiar", "duplicad"]
KEYWORDS_CORRELATION = ["correlaci", "relaci", "patrón", "patron", "asociaci"]
KEYWORDS_OUTLIERS = ["outlier", "atípic", "atipic", "anomal", "iqr", "rango intercuart"]
KEYWORDS_ML = ["modelo", "cluster", "clasificaci", "regresi", "predic", "entrenar", "machine learning", "ml"]
KEYWORDS_PLOTTING = ["gráfic", "grafic", "plot", "histograma", "boxplot", "visualiz", "chart"]


def _exact_schema_block(df: pd.DataFrame) -> str:
    """
    Bloque prioritario y explícito con los nombres EXACTOS de columnas y sus
    dtypes, más una muestra mínima real (head(2)). Su único propósito es que
    la IA nunca tenga que adivinar un nombre de columna (evita KeyError).
    """
    columns = df.columns.tolist()
    truncated = len(columns) > MAX_COLUMNS_IN_METADATA
    listed_columns = columns[:MAX_COLUMNS_IN_METADATA] if truncated else columns

    schema_lines = [f"  - {repr(c)} → {t}" for c, t in zip(listed_columns, df[listed_columns].dtypes.astype(str))]

    header = (
        "### ESQUEMA EXACTO DEL DATAFRAME (usa estos nombres LITERALMENTE, no los adivines)\n"
        f"- Dimensiones (df.shape): {df.shape[0]} filas × {df.shape[1]} columnas\n"
        f"- Columnas y tipos exactos (df.columns.tolist() + dtypes)"
        + (f" — mostrando {MAX_COLUMNS_IN_METADATA} de {len(columns)}:" if truncated else ":")
        + "\n" + "\n".join(schema_lines)
    )

    head_sample = "\n**Muestra real df.head(2):**\n" + df.head(2).to_markdown(index=False)

    return header + "\n" + head_sample


def _base_metadata(df: pd.DataFrame) -> str:
    lines = [_exact_schema_block(df)]

    if len(df) > N_HEAD_ROWS:
        sample_n = min(N_SAMPLE_ROWS, len(df))
        lines.append(
            "\n**Muestra aleatoria adicional df.sample(3):**\n"
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
            vc = df[c].value_counts().head(N_TOP_CATEGORIES)
            nuniq = int(df[c].nunique(dropna=False))
            sample = ", ".join(f"{i}={v}" for i, v in vc.items())
            top_vals.append(f"  - {c}: uniques={nuniq}, top: {sample}")
        lines.append("\n**Top valores categóricos (n unique y top N):**\n" + "\n".join(top_vals))

    return "\n".join(lines)


def _detect_intents(query: str) -> set[str]:
    q = query.lower()
    intents = set()
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


def _extra_block_cleaning(df: pd.DataFrame) -> str:
    dup = int(df.duplicated().sum())
    return (
        f"\n### Contexto extra — Limpieza/Nulos\n"
        f"- Filas totalmente duplicadas: {dup}\n"
        f"- Nulos detallados: {df.isnull().sum().to_dict()}"
    )


def _extra_block_correlation(df: pd.DataFrame) -> str:
    num_cols = numeric_columns(df)
    if len(num_cols) < 2:
        return "\n### Contexto extra — Correlaciones\nNo hay suficientes columnas numéricas."
    corr = df[num_cols].corr(numeric_only=True).round(2)
    return f"\n### Contexto extra — Correlaciones (df.corr resumido)\n{corr.to_markdown()}"


def _extra_block_outliers(df: pd.DataFrame) -> str:
    num_cols = numeric_columns(df)
    rows = []
    for c in num_cols:
        q1, q3 = df[c].quantile(0.25), df[c].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((df[c] < lower) | (df[c] > upper)).sum())
        rows.append(f"  - {c}: IQR=[{q1:.2f}, {q3:.2f}], límites=[{lower:.2f}, {upper:.2f}], outliers≈{n_out}")
    return "\n### Contexto extra — Outliers (rango intercuartílico)\n" + "\n".join(rows)


def _extra_block_ml(df: pd.DataFrame) -> str:
    num_cols = numeric_columns(df)
    rows = [f"  - {c}: min={df[c].min():.2f}, max={df[c].max():.2f}, media={df[c].mean():.2f}" for c in num_cols]
    return "\n### Contexto extra — ML/Clustering (rangos numéricos)\n" + "\n".join(rows)


def _extra_block_plotting(df: pd.DataFrame, query: str) -> str:
    mentioned = [c for c in df.columns if re.search(rf"\b{re.escape(str(c))}\b", query, re.IGNORECASE)]
    cols = mentioned if mentioned else df.columns.tolist()[:5]
    return f"\n### Contexto extra — Gráficos (columnas relevantes)\nColumnas mencionadas o sugeridas: {cols}"


def build_context(df: pd.DataFrame, user_query: str) -> str:
    """Construye el bloque de contexto completo: metadata base + bloques adaptativos."""
    blocks = [_base_metadata(df)]

    intents = _detect_intents(user_query)
    if "cleaning" in intents:
        blocks.append(_extra_block_cleaning(df))
    if "correlation" in intents:
        blocks.append(_extra_block_correlation(df))
    if "outliers" in intents:
        blocks.append(_extra_block_outliers(df))
    if "ml" in intents:
        blocks.append(_extra_block_ml(df))
    if "plotting" in intents:
        blocks.append(_extra_block_plotting(df, user_query))

    return "\n".join(blocks)
