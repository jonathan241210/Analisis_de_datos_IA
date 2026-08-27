import builtins as _builtins
import concurrent.futures
import contextlib
import io
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from sklearn import (
    cluster,
    decomposition,
    ensemble,
    linear_model,
    metrics,
    model_selection,
    preprocessing,
    tree,
)

from app.core.config import settings
from app.domain.models import ExecutionResult
from app.sandbox.validator import ALLOWED_IMPORT_MODULES, UnsafeCodeError, validate_ast
from app.services.plotly_json import fig_to_dict

logger = logging.getLogger("analisis_ia")

UI_EXECUTE_ERROR = "No se pudo ejecutar el código."
UI_TIMEOUT_ERROR = "La ejecución superó el tiempo máximo."


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name not in ALLOWED_IMPORT_MODULES:
        raise UnsafeCodeError(f"Import no permitido: '{name}'")
    return _builtins.__import__(name, globals, locals, fromlist, level)


def _serialize_fig(fig) -> dict | None:
    if fig is None:
        return None
    if isinstance(fig, go.Figure):
        return fig_to_dict(fig)
    return None


_orig_select = np.select


def _select_compat(condlist, choicelist, default=0, **kwargs):
    try:
        return _orig_select(condlist, choicelist, default=default, **kwargs)
    except TypeError:
        zero_default = default == 0 and not isinstance(default, (str, bytes))
        if zero_default:
            return _orig_select(condlist, choicelist, default="", **kwargs)
        raise


class _NpSandbox:
    """Expose numpy, with select() tolerant of string choices + default=0."""

    def __getattr__(self, name):
        if name == "select":
            return _select_compat
        return getattr(np, name)


def _run(code: str, df: pd.DataFrame) -> ExecutionResult:
    validate_ast(code)

    safe_builtins = {
        "len": len, "range": range, "list": list, "dict": dict, "set": set,
        "tuple": tuple, "str": str, "int": int, "float": float, "bool": bool,
        "sum": sum, "min": min, "max": max, "sorted": sorted, "enumerate": enumerate,
        "zip": zip, "map": map, "filter": filter, "abs": abs, "round": round,
        "print": print, "isinstance": isinstance, "type": type, "Exception": Exception,
        "__import__": _safe_import,
    }
    local_ns = {
        "df": df.copy(),
        "pd": pd, "np": _NpSandbox(), "plt": plt, "sns": sns,
        "px": px, "go": go,
        "linear_model": linear_model, "ensemble": ensemble, "tree": tree,
        "cluster": cluster, "decomposition": decomposition,
        "preprocessing": preprocessing, "model_selection": model_selection,
        "metrics": metrics,
        "fig": None,
    }
    global_ns = {"__builtins__": safe_builtins}
    stdout_buffer = io.StringIO()
    try:
        plt.close("all")
        with contextlib.redirect_stdout(stdout_buffer):
            exec(code, global_ns, local_ns)  # noqa: S102 — sandbox only, AST-validated
        result_df = local_ns.get("df")
        result_fig = local_ns.get("fig")
        display_df = local_ns.get("display_df")
        if display_df is None:
            candidates = [
                v for k, v in local_ns.items()
                if k not in {"df"} and not str(k).startswith("_") and isinstance(v, pd.DataFrame)
            ]
            if candidates:
                display_df = min(candidates, key=lambda frame: frame.shape[0])
        if result_fig is None and plt.get_fignums():
            result_fig = plt.gcf()
        return ExecutionResult(
            success=True,
            df=result_df if isinstance(result_df, pd.DataFrame) else df,
            display_df=display_df if isinstance(display_df, pd.DataFrame) else None,
            fig=_serialize_fig(result_fig),
            stdout=stdout_buffer.getvalue(),
        )
    except UnsafeCodeError as exc:
        logger.warning("Sandbox rejected code: %s", exc)
        return ExecutionResult(success=False, error=UI_EXECUTE_ERROR, stdout=stdout_buffer.getvalue())
    except Exception:
        logger.exception("Sandbox execution failed")
        return ExecutionResult(
            success=False,
            error=UI_EXECUTE_ERROR,
            stdout=stdout_buffer.getvalue(),
        )


def run_generated_code(code: str, df: pd.DataFrame) -> ExecutionResult:
    try:
        validate_ast(code)
    except UnsafeCodeError as exc:
        logger.warning("Sandbox rejected code: %s", exc)
        return ExecutionResult(success=False, error=UI_EXECUTE_ERROR)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run, code, df)
        try:
            return future.result(timeout=settings.sandbox_timeout_s)
        except concurrent.futures.TimeoutError:
            logger.warning("Sandbox execution timed out after %ss", settings.sandbox_timeout_s)
            return ExecutionResult(success=False, error=UI_TIMEOUT_ERROR)
