import io

import pandas as pd


def human_readable_bytes(n: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def normalize_column_labels(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def resolve_columns(df: pd.DataFrame, requested: list[str] | None) -> list[str]:
    """Map request names to real columns (exact, then stripped)."""
    items = [str(c) for c in (requested or []) if str(c).strip()]
    exact = {str(c): c for c in df.columns}
    stripped = {str(c).strip(): c for c in df.columns}
    found: list = []
    seen: set = set()
    for raw in items:
        name = exact.get(raw) or exact.get(raw.strip()) or stripped.get(raw.strip())
        if name is None or name in seen:
            continue
        seen.add(name)
        found.append(name)
    return found


def requested_column_list(columns: list[str] | str | None, column: str | None = None) -> list[str]:
    items: list[str] = []
    if isinstance(columns, str):
        items.append(columns)
    elif columns:
        items.extend(str(c) for c in columns)
    if column:
        items.append(column)
    return [c for c in items if c]


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include="number").columns.tolist()


def categorical_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=["object", "string", "category", "bool"]).columns.tolist()


def datetime_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def zero_variance_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in numeric_columns(df) if df[c].nunique(dropna=True) <= 1]


def safe_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    n = min(n, len(df))
    if n <= 0:
        return df.head(0)
    return df.sample(n=n, random_state=42)


def df_preview(df: pd.DataFrame, n: int = 20) -> dict:
    head = df.head(n)
    records: list[dict] = []
    for row in head.itertuples(index=False):
        item: dict = {}
        for col, val in zip(df.columns, row):
            if pd.isna(val):
                item[str(col)] = None
            elif hasattr(val, "item"):
                item[str(col)] = val.item()
            else:
                item[str(col)] = val
        records.append(item)
    return {
        "columns": [str(c) for c in df.columns],
        "dtypes": {str(c): str(t) for c, t in df.dtypes.items()},
        "rows": records,
        "shape": [int(df.shape[0]), int(df.shape[1])],
        "memory": human_readable_bytes(float(df.memory_usage(deep=True).sum())),
        "duplicate_rows": int(df.duplicated().sum()),
    }
