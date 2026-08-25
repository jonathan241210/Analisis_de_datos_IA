"""
utils/helpers.py
Funciones auxiliares reutilizables entre módulos.
"""
import io
import pandas as pd


def human_readable_bytes(n: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include="number").columns.tolist()


def categorical_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()


def datetime_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def zero_variance_columns(df: pd.DataFrame) -> list[str]:
    cols = []
    for c in numeric_columns(df):
        if df[c].nunique(dropna=True) <= 1:
            cols.append(c)
    return cols


def safe_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    n = min(n, len(df))
    if n <= 0:
        return df.head(0)
    return df.sample(n=n, random_state=42)
