import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

from app.core.exceptions import AppError
from app.services.dataframe_ops import categorical_columns, numeric_columns, resolve_columns


def apply_wrangling(df: pd.DataFrame, op: str, **kwargs) -> pd.DataFrame:
    handlers = {
        "impute": _impute,
        "drop_duplicates": _drop_duplicates,
        "cast": _cast,
        "scale": _scale,
        "encode": _encode,
        "rename": _rename,
        "drop_columns": _drop_columns,
    }
    if op not in handlers:
        raise AppError(f"Operación desconocida: {op}", 400)
    return handlers[op](df.copy(), **kwargs)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    wanted = [c for c in (columns or []) if str(c).strip()]
    found = resolve_columns(df, wanted)
    have = {str(c).strip() for c in found}
    missing = [c for c in wanted if str(c).strip() not in have]
    if missing:
        raise AppError(f"Columnas inexistentes: {missing}", 400)
    return found


def _impute(df: pd.DataFrame, columns: list[str] | None = None, strategy: str = "Media", value: str | None = None, **_) -> pd.DataFrame:
    target = _require_columns(df, columns or [])
    if strategy == "Eliminar filas":
        return df.dropna(subset=target if target else None)
    if not target:
        raise AppError("Selecciona columnas a imputar.", 400)
    for c in target:
        if strategy == "Media" and pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].fillna(df[c].mean())
        elif strategy == "Mediana" and pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].fillna(df[c].median())
        elif strategy == "Moda":
            mode = df[c].mode(dropna=True)
            if not mode.empty:
                df[c] = df[c].fillna(mode.iloc[0])
        elif strategy == "Constante":
            df[c] = df[c].fillna(value)
        else:
            raise AppError(f"Estrategia '{strategy}' no aplica a '{c}'.", 400)
    return df


def _drop_duplicates(df: pd.DataFrame, **_) -> pd.DataFrame:
    return df.drop_duplicates().reset_index(drop=True)


def _cast(df: pd.DataFrame, columns: list[str] | None = None, target_type: str = "string", **_) -> pd.DataFrame:
    cols = _require_columns(df, columns or [])
    if not cols:
        raise AppError("Selecciona al menos una columna a convertir.", 400)
    for col in cols:
        if target_type == "string":
            df[col] = df[col].astype(str)
        elif target_type == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif target_type == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif target_type == "category":
            df[col] = df[col].astype("category")
        else:
            raise AppError(f"Tipo destino no soportado: {target_type}", 400)
    return df


def _scale(df: pd.DataFrame, columns: list[str] | None = None, method: str = "StandardScaler", **_) -> pd.DataFrame:
    cols = [c for c in resolve_columns(df, columns or []) if c in numeric_columns(df)]
    if not cols:
        raise AppError("Selecciona columnas numéricas para escalar.", 400)
    scaler = StandardScaler() if method == "StandardScaler" else MinMaxScaler()
    df[cols] = scaler.fit_transform(df[cols])
    return df


def _encode(df: pd.DataFrame, columns: list[str] | None = None, method: str = "One-Hot Encoding", **_) -> pd.DataFrame:
    resolved = resolve_columns(df, columns or [])
    cats = set(categorical_columns(df))
    cols = [c for c in resolved if c in cats or c in df.columns]
    if not cols:
        raise AppError("Selecciona columnas categóricas a codificar.", 400)
    _require_columns(df, cols)
    if method == "One-Hot Encoding":
        return pd.get_dummies(df, columns=cols, drop_first=False)
    for c in cols:
        df[c] = LabelEncoder().fit_transform(df[c].astype(str))
    return df


def _rename(df: pd.DataFrame, columns: list[str] | None = None, new_name: str | None = None, **_) -> pd.DataFrame:
    cols = _require_columns(df, columns or [])
    if not cols or not new_name:
        raise AppError("Indica la columna y el nuevo nombre.", 400)
    return df.rename(columns={cols[0]: new_name})


def _drop_columns(df: pd.DataFrame, columns: list[str] | None = None, **_) -> pd.DataFrame:
    cols = _require_columns(df, columns or [])
    if not cols:
        raise AppError("Selecciona columnas a eliminar.", 400)
    return df.drop(columns=cols)
