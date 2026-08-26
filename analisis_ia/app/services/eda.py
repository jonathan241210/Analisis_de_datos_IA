import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.services.dataframe_ops import (
    categorical_columns,
    human_readable_bytes,
    numeric_columns,
    resolve_columns,
    zero_variance_columns,
)


from app.services.plotly_json import fig_to_dict


def _fig_json(fig) -> dict:
    return fig_to_dict(fig)


def general_metrics(df: pd.DataFrame) -> dict:
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "memory": human_readable_bytes(float(df.memory_usage(deep=True).sum())),
        "duplicate_rows": int(df.duplicated().sum()),
        "zero_variance_columns": zero_variance_columns(df),
        "dtypes": [{"columna": str(c), "tipo": str(t)} for c, t in zip(df.columns, df.dtypes)],
    }


def descriptive_stats(df: pd.DataFrame) -> dict:
    num_cols = numeric_columns(df)
    numeric = []
    if num_cols:
        desc = df[num_cols].describe().T.reset_index().rename(columns={"index": "columna"})
        numeric = desc.to_dict(orient="records")
        for row in numeric:
            for k, v in list(row.items()):
                if hasattr(v, "item"):
                    row[k] = v.item()

    cat_rows = []
    for c in categorical_columns(df):
        vc = df[c].value_counts(dropna=False)
        top = ", ".join(f"{i}={v}" for i, v in vc.head(5).items())
        cat_rows.append({
            "columna": str(c),
            "n_unique": int(df[c].nunique(dropna=False)),
            "top_values": top,
        })
    return {"numeric": numeric, "categorical": cat_rows}


def quality_diagnosis(df: pd.DataFrame) -> dict:
    nulls = df.isnull().sum()
    pct = (nulls / len(df) * 100).round(2) if len(df) else nulls
    rows = []
    for col in df.columns:
        rows.append({
            "columna": str(col),
            "nulos": int(nulls[col]),
            "pct_nulos": float(pct[col]),
            "tipo": str(df[col].dtype),
        })
    rows.sort(key=lambda r: r["nulos"], reverse=True)
    return {"columns": rows, "zero_variance": zero_variance_columns(df)}


def value_counts_table(df: pd.DataFrame, column: str, limit: int = 50) -> dict:
    if column not in df.columns:
        raise ValueError(f"Columna desconocida: {column}")
    vc = df[column].value_counts(dropna=False).head(limit).reset_index()
    vc.columns = [str(column), "count"]
    rows = []
    for row in vc.itertuples(index=False):
        key, count = row[0], row[1]
        if pd.isna(key):
            key = None
        elif hasattr(key, "item"):
            key = key.item()
        rows.append({str(column): key, "count": int(count)})
    return {"columns": [str(column), "count"], "rows": rows}


def histogram_spec(df: pd.DataFrame, columns: list[str] | str) -> dict:
    if isinstance(columns, str):
        columns = [columns]
    cols = resolve_columns(df, columns)
    if not cols:
        split: list[str] = []
        for item in columns:
            split.extend(part for part in str(item).split(",") if part.strip())
        cols = resolve_columns(df, split)
    if not cols:
        raise ValueError("Selecciona al menos una columna para el histograma.")
    if len(cols) == 1:
        fig = px.histogram(df, x=cols[0], nbins=40, title=f"Distribución de {cols[0]}")
        fig.update_layout(height=420, autosize=True, margin={"l": 56, "r": 28, "t": 64, "b": 48})
        return _fig_json(fig)
    spacing = min(0.08, 0.55 / max(len(cols) - 1, 1))
    fig = make_subplots(rows=len(cols), cols=1, subplot_titles=cols, vertical_spacing=spacing)
    for i, col in enumerate(cols, start=1):
        fig.add_trace(
            go.Histogram(x=df[col], nbinsx=40, name=col, showlegend=False),
            row=i,
            col=1,
        )
    fig.update_layout(
        title="Histogramas",
        height=max(400, 360 * len(cols)),
        bargap=0.05,
        autosize=True,
        margin={"l": 56, "r": 28, "t": 72, "b": 48},
    )
    return _fig_json(fig)


def boxplot_spec(df: pd.DataFrame, columns: list[str]) -> dict:
    cols = [c for c in resolve_columns(df, columns) if c in numeric_columns(df)]
    if not cols:
        raise ValueError("Selecciona al menos una columna numérica.")
    if len(cols) == 1:
        fig = px.box(df, y=cols[0], points="outliers", title=f"Boxplot de {cols[0]}")
        fig.update_layout(height=420, autosize=True, margin={"l": 56, "r": 28, "t": 64, "b": 48})
        return _fig_json(fig)
    spacing = min(0.08, 0.55 / max(len(cols) - 1, 1))
    fig = make_subplots(rows=len(cols), cols=1, subplot_titles=cols, vertical_spacing=spacing)
    for i, col in enumerate(cols, start=1):
        fig.add_trace(
            go.Box(y=df[col], name=col, showlegend=False, boxmean=True),
            row=i,
            col=1,
        )
    fig.update_layout(
        title="Boxplots — detección de atípicos",
        height=max(400, 360 * len(cols)),
        autosize=True,
        margin={"l": 56, "r": 28, "t": 72, "b": 48},
    )
    return _fig_json(fig)


def correlation_spec(df: pd.DataFrame) -> dict:
    num_cols = numeric_columns(df)
    if len(num_cols) < 2:
        raise ValueError("Se necesitan al menos 2 columnas numéricas.")
    corr = df[num_cols].corr(numeric_only=True)
    fig = px.imshow(
        corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r",
        title="Matriz de correlación",
        height=max(420, 48 * len(num_cols) + 160),
        autosize=True,
        margin={"l": 80, "r": 28, "t": 64, "b": 80},
    )
    return _fig_json(fig)


def build_eda_report(df: pd.DataFrame) -> dict:
    num_cols = numeric_columns(df)
    cat_cols = categorical_columns(df)
    return {
        "metrics": general_metrics(df),
        "stats": descriptive_stats(df),
        "quality": quality_diagnosis(df),
        "numeric_columns": num_cols,
        "categorical_columns": cat_cols,
    }
