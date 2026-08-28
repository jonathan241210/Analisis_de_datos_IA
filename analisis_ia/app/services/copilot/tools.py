from __future__ import annotations

import json
from typing import Any

import pandas as pd

from app.core.config import settings
from app.core.exceptions import AppError
from app.sandbox.executor import run_generated_code
from app.services.dataframe_ops import categorical_columns, df_preview, numeric_columns
from app.services.wrangling import apply_wrangling

ALLOWED_MUTATION_OPS = {
    "impute",
    "drop_duplicates",
    "cast",
    "scale",
    "encode",
    "rename",
    "drop_columns",
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "inspect_dataset",
        "description": (
            "Inspecciona metadata del DataFrame activo (no son los datos completos): "
            "esquema, nulos, duplicados, outliers IQR, pistas para ML. "
            "Si la petición del usuario es vaga, usa focus=all."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "enum": ["all", "schema", "nulls", "duplicates", "outliers", "ml"],
                    "description": "Qué revisar. all = auditoría completa.",
                }
            },
        },
    },
    {
        "name": "run_python",
        "description": (
            "Ejecuta Python de solo lectura en el sandbox (df, pd, np, px, go, sklearn). "
            "No importa módulos. Gráficas: asigna fig (Plotly). Tablas auxiliares: display_df. "
            "Si el código mutara df, el cambio NO se aplica; usa propose_mutations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Código Python validado por AST."},
                "purpose": {
                    "type": "string",
                    "enum": ["inspect", "plot", "table", "other"],
                    "description": "Motivo: inspeccionar, graficar, tabla u otro.",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "propose_mutations",
        "description": (
            "Propone transformaciones para que el usuario confirme (no las aplica). "
            "ops: impute, drop_duplicates, cast, scale, encode, rename, drop_columns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "op": {"type": "string"},
                            "label": {"type": "string", "description": "Texto corto del botón, en español."},
                            "columns": {"type": "array", "items": {"type": "string"}},
                            "strategy": {"type": "string"},
                            "value": {"type": "string"},
                            "target_type": {"type": "string"},
                            "method": {"type": "string"},
                            "new_name": {"type": "string"},
                        },
                        "required": ["op", "label"],
                    },
                }
            },
            "required": ["actions"],
        },
    },
]


def json_safe(obj: Any, limit: int = 8000) -> Any:
    def conv(value: Any) -> Any:
        if value is None or isinstance(value, (bool, str, int, float)):
            return value
        if hasattr(value, "item") and not isinstance(value, (bytes, str)):
            try:
                return conv(value.item())
            except Exception:
                return str(value)
        if isinstance(value, dict):
            return {str(k): conv(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [conv(v) for v in value]
        return str(value)

    converted = conv(obj)
    text = json.dumps(converted, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return converted
    return {"truncated": True, "preview": text[:limit]}


def inspect_dataset(df: pd.DataFrame, focus: str = "all") -> dict[str, Any]:
    key = (focus or "all").strip().lower()
    if key not in {"all", "schema", "nulls", "duplicates", "outliers", "ml"}:
        key = "all"
    payload: dict[str, Any] = {
        "focus": key,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
    }
    if key in {"all", "schema"}:
        listed = df.columns.tolist()[: settings.max_columns_in_metadata]
        payload["schema"] = [{"name": str(c), "dtype": str(df[c].dtype)} for c in listed]
        payload["head"] = df.head(2).astype(str).to_dict(orient="records")
    if key in {"all", "nulls"}:
        null_counts = df.isnull().sum()
        n = len(df) or 1
        payload["nulls"] = [
            {"column": str(c), "count": int(null_counts[c]), "pct": round(float(null_counts[c]) / n * 100, 1)}
            for c in df.columns
            if int(null_counts[c]) > 0
        ]
        if not payload["nulls"]:
            payload["nulls"] = []
            payload["nulls_note"] = "ninguna columna tiene nulos"
    if key in {"all", "duplicates"}:
        payload["duplicate_rows"] = int(df.duplicated().sum())
    if key in {"all", "outliers"}:
        rows = []
        for c in numeric_columns(df):
            q1, q3 = df[c].quantile(0.25), df[c].quantile(0.75)
            iqr = q3 - q1
            if pd.isna(iqr):
                continue
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            n_out = int(((df[c] < lower) | (df[c] > upper)).sum())
            rows.append({"column": str(c), "outliers_iqr": n_out})
        payload["outliers"] = rows
    if key in {"all", "ml"}:
        num_cols = numeric_columns(df)
        cat_cols = categorical_columns(df)
        payload["numeric"] = []
        for c in num_cols[:20]:
            series = df[c].dropna()
            payload["numeric"].append(
                {
                    "column": str(c),
                    "min": None if series.empty else float(series.min()),
                    "max": None if series.empty else float(series.max()),
                    "nunique": int(df[c].nunique(dropna=True)),
                }
            )
        payload["categorical"] = []
        for c in cat_cols[:20]:
            payload["categorical"].append(
                {
                    "column": str(c),
                    "nunique": int(df[c].nunique(dropna=True)),
                }
            )
        id_like = [str(c) for c in df.columns if str(c).lower() in {"id", "index"} or str(c).lower().endswith("_id")]
        payload["likely_identifiers"] = id_like
        low_card = [c for c in cat_cols if 2 <= int(df[c].nunique(dropna=True)) <= 12]
        payload["possible_classification_targets"] = low_card[:8]
    return json_safe(payload)


def run_python_readonly(df: pd.DataFrame, code: str) -> tuple[dict[str, Any], dict[str, Any]]:
    result = run_generated_code(code or "", df)
    mutated = bool(result.success and result.df is not None and not result.df.equals(df))
    payload: dict[str, Any] = {
        "success": result.success,
        "error": result.error,
        "stdout": (result.stdout or "")[:4000],
        "mutated_in_sandbox": mutated,
        "applied": False,
        "has_fig": bool(result.fig),
    }
    if mutated:
        payload["note"] = (
            "El código habría modificado df; el cambio NO se aplicó. "
            "Usa propose_mutations y espera la confirmación del usuario."
        )
    extra: dict[str, Any] = {}
    if result.success and result.display_df is not None:
        extra["display"] = df_preview(result.display_df, min(20, len(result.display_df)))
        payload["display_rows"] = int(result.display_df.shape[0])
        payload["display_cols"] = int(result.display_df.shape[1])
    if result.fig:
        extra["fig"] = result.fig
    return json_safe(payload), extra


def propose_mutations(actions: list[dict[str, Any]] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cleaned: list[dict[str, Any]] = []
    for raw in actions or []:
        if not isinstance(raw, dict):
            continue
        op = str(raw.get("op") or "").strip()
        if op not in ALLOWED_MUTATION_OPS:
            continue
        label = str(raw.get("label") or op).strip()
        action = {
            "op": op,
            "label": label,
            "columns": [str(c) for c in (raw.get("columns") or []) if str(c).strip()],
            "strategy": raw.get("strategy"),
            "value": raw.get("value"),
            "target_type": raw.get("target_type"),
            "method": raw.get("method"),
            "new_name": raw.get("new_name"),
        }
        cleaned.append(action)
    return {"accepted": len(cleaned), "rejected_unknown_ops": max(0, len(actions or []) - len(cleaned))}, cleaned


def step_label(name: str, args: dict[str, Any] | None) -> str:
    args = args or {}
    if name == "inspect_dataset":
        focus = str(args.get("focus") or "all").lower()
        return {
            "nulls": "Revisando nulos…",
            "duplicates": "Buscando duplicados…",
            "outliers": "Revisando outliers…",
            "schema": "Revisando esquema…",
            "ml": "Evaluando variables para ML…",
            "all": "Revisando el dataset…",
        }.get(focus, "Revisando el dataset…")
    if name == "run_python":
        purpose = str(args.get("purpose") or "other").lower()
        return {
            "plot": "Graficando…",
            "inspect": "Calculando métricas…",
            "table": "Armando tabla…",
            "other": "Ejecutando análisis…",
        }.get(purpose, "Ejecutando análisis…")
    if name == "propose_mutations":
        return "Proponiendo limpieza…"
    return "Trabajando…"


def dispatch_tool(df: pd.DataFrame, name: str, args: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    args = args or {}
    if name == "inspect_dataset":
        return inspect_dataset(df, str(args.get("focus") or "all")), {}
    if name == "run_python":
        return run_python_readonly(df, str(args.get("code") or ""))
    if name == "propose_mutations":
        payload, actions = propose_mutations(args.get("actions"))
        return payload, {"proposed_actions": actions}
    return {"error": f"Herramienta desconocida: {name}"}, {}


def apply_confirmed_action(df: pd.DataFrame, action: dict[str, Any]) -> pd.DataFrame:
    op = str(action.get("op") or "")
    if op not in ALLOWED_MUTATION_OPS:
        raise AppError("Operación no permitida.", 400)
    return apply_wrangling(
        df,
        op,
        columns=action.get("columns") or [],
        strategy=action.get("strategy") or "Media",
        value=action.get("value"),
        target_type=action.get("target_type") or "string",
        method=action.get("method") or "StandardScaler",
        new_name=action.get("new_name"),
    )
