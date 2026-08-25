"""
modules/ai_copilot/executor.py
Entorno de ejecución seguro/controlado para el código Python generado por la IA.

Estrategia de seguridad (defensa en profundidad, no es un sandbox de nivel
sistema operativo — para eso se recomienda contenerizar el proceso de Streamlit):
  1. Validación estática con AST: se rechazan imports fuera de una lista blanca,
     accesos a dunders, y llamadas a funciones peligrosas (eval, exec, open,
     __import__, compile, os.system, subprocess, etc.).
  2. Namespace de ejecución restringido: solo se exponen los builtins seguros y
     las librerías de análisis de datos ya importadas (pd, np, plt, sns, px, sklearn).
  3. El código SIEMPRE opera sobre una copia de `df`; solo se reemplaza la copia
     en sesión si la ejecución termina sin errores.
  4. stdout se captura y se devuelve como texto en vez de imprimirse en la consola
     del servidor.
"""
import ast
import io
import builtins as _builtins
import contextlib
import re
import difflib

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from sklearn import (
    linear_model, ensemble, tree, cluster, decomposition, preprocessing,
    model_selection, metrics,
)
import streamlit as st


class UnsafeCodeError(Exception):
    pass


class ExecutionResult:
    def __init__(self, success, df=None, fig=None, stdout="", error=None, display_df=None):
        self.success = success
        # `df` es la copia del DataFrame principal (posible actualización global)
        self.df = df
        # `display_df` es un DataFrame auxiliar que se generó en el código y
        # que debe mostrarse al usuario sin sobrescribir la tabla global.
        self.display_df = display_df
        self.fig = fig
        self.stdout = stdout
        self.error = error


ALLOWED_IMPORT_MODULES = {
    "pandas", "numpy", "matplotlib", "matplotlib.pyplot", "seaborn",
    "plotly", "plotly.express", "plotly.graph_objects", "sklearn",
    "scipy", "scipy.stats",
}

FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "exit", "quit", "help", "breakpoint",
}

FORBIDDEN_MODULE_PATTERNS = re.compile(
    r"^(os|sys|subprocess|shutil|socket|pathlib|requests|urllib|http|"
    r"pickle|importlib|ctypes|multiprocessing|threading)(\.|$)"
)


def _validate_ast(code: str):
    try:
        tree_ = ast.parse(code, mode="exec")
    except SyntaxError as e:
        raise UnsafeCodeError(f"Error de sintaxis en el código generado: {e}")

    for node in ast.walk(tree_):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module_names = (
                [n.name for n in node.names] if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            for name in module_names:
                if name not in ALLOWED_IMPORT_MODULES:
                    raise UnsafeCodeError(f"Import no permitido: '{name}'")

        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise UnsafeCodeError(f"Uso no permitido de: '{node.id}'")

        if isinstance(node, ast.Attribute):
            if isinstance(node.attr, str) and node.attr.startswith("__") and node.attr.endswith("__"):
                raise UnsafeCodeError(f"Acceso no permitido a atributo dunder: '{node.attr}'")

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            full_ref = _attr_chain(node.func)
            if full_ref and FORBIDDEN_MODULE_PATTERNS.match(full_ref):
                raise UnsafeCodeError(f"Llamada no permitida: '{full_ref}(...)'")


def _attr_chain(node: ast.Attribute) -> str:
    parts = [node.attr]
    cur = node.value
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def extract_python_code(markdown_text: str) -> list[str]:
    """Extrae todos los bloques ```python ... ``` de una respuesta de la IA."""
    pattern = r"```python\s*(.*?)```"
    return [block.strip() for block in re.findall(pattern, markdown_text, re.DOTALL)]


def _collect_names(code: str):
    """Return a tuple (assigned_names_set, used_names_set) from AST analysis."""
    assigned = set()
    used = set()
    try:
        tree_ = ast.parse(code, mode="exec")
    except SyntaxError:
        return assigned, used

    for node in ast.walk(tree_):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                assigned.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                used.add(node.id)
    return assigned, used


def _auto_fix_undefined_names(code: str, allowed_names: set) -> tuple[str, list[tuple[str,str]]]:
    """Detect names used but not defined/allowed and try to auto-correct by similarity.

    Returns (new_code, list_of_fixes) where each fix is (bad_name, replacement).
    """
    assigned, used = _collect_names(code)
    fixes = []

    candidates = list(assigned | allowed_names)
    for name in sorted(used):
        if name in allowed_names or name in assigned or name in ("pd","np","px","go","plt","sns","df"):
            continue
        # find close match among assigned names
        match = difflib.get_close_matches(name, candidates, n=1, cutoff=0.7)
        if match:
            repl = match[0]
            # replace whole-word occurrences
            pattern = rf"\b{re.escape(name)}\b"
            new_code, n = re.subn(pattern, repl, code)
            if n > 0:
                fixes.append((name, repl))
                code = new_code
                # update assigned/candidates for subsequent iterations
                assigned.add(repl)
                candidates = list(assigned | allowed_names)

    return code, fixes


def _fix_px_table_calls(code: str) -> tuple[str, list[str]]:
    """Reemplaza llamadas a `px.table(df, ...)` por una construcción con `go.Table`.

    Devuelve (new_code, replacements_list) con pares informativos.
    """
    replacements = []

    def _find_matching_paren(s: str, start_idx: int) -> int:
        depth = 0
        for i in range(start_idx, len(s)):
            if s[i] == '(':
                depth += 1
            elif s[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
        return -1

    i = 0
    out = []
    while True:
        m = re.search(r"px\.table\s*\(", code[i:])
        if not m:
            out.append(code[i:])
            break
        start = i + m.start()
        open_paren = i + m.end() - 1  # position of '('
        close_paren = _find_matching_paren(code, open_paren)
        if close_paren == -1:
            # unmatched, abort replacement
            out.append(code[i:])
            break
        # extract the entire call
        call_text = code[start:close_paren+1]
        # extract inner argument expression
        inner = code[open_paren+1:close_paren].strip()
        # build replacement code
        table_code = (
            f"fig = go.Figure(go.Table("
            f"header=dict(values=list({inner}.columns)),"
            f"cells=dict(values=[{inner}[c].tolist() for c in {inner}.columns])"
            f"))"
        )
        replacements.append((call_text, table_code))
        out.append(code[i:start])
        out.append(table_code)
        i = close_paren+1

    new_code = "".join(out)
    return new_code, [r[0] for r in replacements]


def _prune_plots_if_head_only(code: str) -> tuple[str, bool]:
    """Si el código contiene `.head(` y no contiene intención explícita de graficar,
    eliminar líneas que generan figuras para respetar peticiones del usuario que
    solo piden mostrar filas.

    Devuelve (new_code, pruned_flag).
    """
    # Si hay un .head( en el código, asumimos intención de mostrar registros
    if ".head(" not in code:
        return code, False

    lines = code.splitlines()
    pruned = False
    keep = []
    for ln in lines:
        stripped = ln.strip()
        # eliminar líneas que crean figuras o llaman a px/plotly/seaborn/matplotlib
        if re.search(r"\b(px\.|plotly\.|go\.Figure|fig\s*=|fig_\w+\s*=|plt\.|sns\.|st\.plotly_chart)", stripped):
            pruned = True
            continue
        keep.append(ln)

    return "\n".join(keep), pruned


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """__import__ restringido: solo permite las librerías de análisis de datos en la lista blanca."""
    if name not in ALLOWED_IMPORT_MODULES:
        raise UnsafeCodeError(f"Import no permitido: '{name}'")
    return _builtins.__import__(name, globals, locals, fromlist, level)


def _convert_head_prints_and_exprs(code: str) -> tuple[str, bool]:
    """Convierte expresiones sueltas o `print(...)` que muestran porciones
    del DataFrame en `display_df = <expr>` para que la UI pueda renderizar
    correctamente filas+columnas solicitadas.

    Regla heurística:
    - Si un `Expr` a nivel de módulo es una llamada a `print(...)` cuyo
      argumento contiene `.head(`, `.iloc`, `.loc` o es un `Subscript`, se
      reemplaza por `display_df = <arg>`.
    - Si un `Expr` directo contiene `.head(`, `.iloc`, `.loc` o es un
      `Subscript`, se reemplaza por `display_df = <expr>`.
    Devuelve (new_code, converted_flag).
    """
    try:
        tree_ = ast.parse(code, mode="exec")
    except SyntaxError:
        return code, False

    def _node_has_selection(n: ast.AST) -> bool:
        for node in ast.walk(n):
            if isinstance(node, ast.Attribute) and isinstance(node.attr, str) and node.attr in ("head", "iloc", "loc"):
                return True
            if isinstance(node, ast.Subscript):
                return True
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and getattr(node.func, 'attr', '') == 'head':
                return True
        return False

    converted = False
    new_body = []
    # collect expressions that select parts of df
    selection_nodes = []  # tuples (index_in_body, node, expr)
    for idx, node in enumerate(tree_.body):
        if isinstance(node, ast.Expr):
            expr = node.value
            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == 'print' and expr.args:
                arg = expr.args[0]
                if _node_has_selection(arg):
                    selection_nodes.append((idx, node, arg))
                    continue
            if _node_has_selection(expr):
                selection_nodes.append((idx, node, expr))
                continue

    # Try to combine a head-like selection and a column-selection into one chained expr
    combined_done = False
    head_idx = col_idx = None
    head_node = col_node = None
    for i, (_, _, expr) in enumerate(selection_nodes):
        has_head = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and getattr(n.func, 'attr', '') == 'head' for n in ast.walk(expr))
        has_cols = any(isinstance(n, ast.Subscript) or (isinstance(n, ast.Attribute) and getattr(n, 'attr', '') in ('iloc','loc')) for n in ast.walk(expr))
        if has_head and head_node is None:
            head_idx = selection_nodes[i][0]
            head_node = selection_nodes[i][2]
        if has_cols and col_node is None:
            col_idx = selection_nodes[i][0]
            col_node = selection_nodes[i][2]

    if head_node is not None and col_node is not None and head_idx != col_idx:
        # attempt to graft head_node as the value of col_node where col_node references df
        graft = None
        try:
            # If col_node is a Subscript (e.g. df[['a','b']]) replace its value with head_node
            if isinstance(col_node, ast.Subscript):
                new_sub = ast.copy_location(ast.Subscript(value=head_node, slice=col_node.slice, ctx=col_node.ctx), col_node)
                graft = new_sub
            elif isinstance(col_node, ast.Call) and isinstance(col_node.func, ast.Attribute) and getattr(col_node.func, 'attr', '') in ('iloc', 'loc'):
                # e.g. df.iloc[...]
                new_attr = ast.copy_location(ast.Attribute(value=head_node, attr=col_node.func.attr, ctx=ast.Load()), col_node.func)
                new_call = ast.copy_location(ast.Call(func=new_attr, args=col_node.args, keywords=col_node.keywords), col_node)
                graft = new_call
            elif isinstance(col_node, ast.Call) and isinstance(col_node.func, ast.Name) and col_node.func.id == 'print':
                # print(...) handled earlier; unlikely here
                graft = None
        except Exception:
            graft = None

        if graft is not None:
            assign = ast.Assign(targets=[ast.Name(id='display_df', ctx=ast.Store())], value=graft)
            # build new body omitting the original nodes replaced
            for idx, node in enumerate(tree_.body):
                if idx in (head_idx, col_idx):
                    if idx == head_idx:
                        # insert the combined assignment in place of the earlier node
                        new_body.append(assign)
                    # skip both original nodes
                    continue
                new_body.append(node)
            converted = True
            combined_done = True

    if not combined_done:
        # fallback: convert each selection expr to display_df (last one wins)
        for idx, node in enumerate(tree_.body):
            if isinstance(node, ast.Expr):
                expr = node.value
                if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == 'print' and expr.args:
                    arg = expr.args[0]
                    if _node_has_selection(arg):
                        assign = ast.Assign(targets=[ast.Name(id='display_df', ctx=ast.Store())], value=arg)
                        new_body.append(assign)
                        converted = True
                        continue
                if _node_has_selection(expr):
                    assign = ast.Assign(targets=[ast.Name(id='display_df', ctx=ast.Store())], value=expr)
                    new_body.append(assign)
                    converted = True
                    continue
            new_body.append(node)

    if converted:
        tree_.body = new_body
        try:
            new_code = ast.unparse(tree_)
            return new_code, True
        except Exception:
            return code, False

    return code, False


def run_generated_code(code: str, df: pd.DataFrame, allow_streamlit: bool = False) -> ExecutionResult:
    """Ejecuta el código generado por la IA sobre una COPIA de df en un namespace controlado."""
    # Guardar copia del código original para heurísticas post-ejecución
    orig_code = code
    # Primer intento de corrección: si el modelo colocó código en la misma
    # línea que un comentario (ej: "# comentario print(df.head())"), insertamos
    # un salto de línea antes del código para que no quede comentado.
    def _fix_inline_commented_code(code_str: str):
        keywords = ["print(", "fig =", "fig=", "px.", "pd.", "df[", "plt.", "sns.", "for ", "if ", "return "]
        out_lines = []
        fixes = []
        for line in code_str.splitlines():
            if "#" in line:
                hash_idx = line.find("#")
                tail = line[hash_idx+1:]
                # search for any keyword after the '#'
                found_idx = None
                found_kw = None
                for kw in keywords:
                    idx = line.find(kw, hash_idx+1)
                    if idx != -1 and (found_idx is None or idx < found_idx):
                        found_idx = idx
                        found_kw = kw
                if found_idx is not None:
                    # split the line into comment part and code part
                    comment_part = line[:found_idx]
                    code_part = line[found_idx:]
                    out_lines.append(comment_part.rstrip())
                    out_lines.append(code_part.lstrip())
                    fixes.append((line, comment_part, code_part))
                    continue
            out_lines.append(line)
        return "\n".join(out_lines), fixes

    code, inline_fixes = _fix_inline_commented_code(code)

    # Si el código contiene solo una llamada a .head(...) y no quiere graficas,
    # podemos podar las líneas de creación de figuras para respetar la petición.
    code, pruned = _prune_plots_if_head_only(code)

    # Convertir prints/expresiones sueltas que muestran porciones de df en
    # `display_df = ...` para asegurar que la UI muestre filas+columnas exactas.
    code, converted_display = _convert_head_prints_and_exprs(code)

    # Heurística: si el modelo colocó un `import ... as name` y a continuación
    # puso otra sentencia en la misma línea (sin `;`), el AST fallará con
    # "cannot use name as import target". Insertamos un salto de línea entre
    # el import y la siguiente asignación para recuperarnos de este error común.
    try:
        code = re.sub(r"(import\s+[^\n]+?\s+as\s+\w+)\s+(?=[A-Za-z_]\w*\s*=)", r"\1\n", code)
    except Exception:
        pass

    try:
        _validate_ast(code)
    except UnsafeCodeError as e:
        return ExecutionResult(success=False, error=str(e))


    # Intento de autocorrección: detectar nombres usados pero no definidos y
    # reemplazarlos por nombres asignados cercanos (p.ej. empleado_filtro -> empleados_filtro).
    allowed_names = set(["df", "pd", "np", "plt", "sns", "px", "go"]) | set(FORBIDDEN_NAMES)
    code, fixes = _auto_fix_undefined_names(code, allowed_names)

    # Corregir llamadas erróneas a `px.table(...)` (no existe) por una figura
    # `go.Table` equivalente para evitar AttributeError en tiempo de ejecución.
    code, px_repls = _fix_px_table_calls(code)

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
        "pd": pd, "np": np, "plt": plt, "sns": sns,
        "px": px, "go": go,
        "linear_model": linear_model, "ensemble": ensemble, "tree": tree,
        "cluster": cluster, "decomposition": decomposition,
        "preprocessing": preprocessing, "model_selection": model_selection,
        "metrics": metrics,
        "fig": None,
    }
    if allow_streamlit:
        # Exponer `st` solo cuando el llamador lo autoriza explícitamente
        local_ns["st"] = st
    global_ns = {"__builtins__": safe_builtins}

    stdout_buffer = io.StringIO()
    try:
        plt.close("all")
        with contextlib.redirect_stdout(stdout_buffer):
            if fixes:
                print("[executor] Applied name fixes:", ", ".join(f"{a}=>{b}" for a, b in fixes))
            if 'converted_display' in locals() and converted_display:
                print("[executor] Converted DataFrame expression(s) to 'display_df' for UI display")
            exec(code, global_ns, local_ns)

        result_df = local_ns.get("df")
        result_fig = local_ns.get("fig")
        display_df = None

        # Si la transformación AST no creó `display_df` y el código original
        # contenía una expresión `*.head(...)` suelta, evaluamos esa expresión
        # en el namespace actual para obtener la porción exacta solicitada.
        if display_df is None and ".head(" in orig_code:
            try:
                # localizar la primera aparición y extraer la línea/expresión
                idx = orig_code.find(".head(")
                # buscar inicio de línea
                line_start = orig_code.rfind('\n', 0, idx) + 1
                # buscar paréntesis de cierre balanceado
                def _find_matching_paren(s, start_idx):
                    depth = 0
                    for i in range(start_idx, len(s)):
                        if s[i] == '(':
                            depth += 1
                        elif s[i] == ')':
                            depth -= 1
                            if depth == 0:
                                return i
                    return -1

                open_paren = idx + orig_code[idx:].find('(')
                close_paren = _find_matching_paren(orig_code, open_paren)
                if close_paren != -1:
                    # tomar desde inicio de línea hasta el cierre del paréntesis
                    expr_text = orig_code[line_start:close_paren+1].strip()
                    # evitar líneas que sean asignaciones
                    if '=' not in expr_text.split('\n')[0]:
                        try:
                            val = eval(expr_text, global_ns, local_ns)
                            if isinstance(val, pd.DataFrame):
                                display_df = val
                        except Exception:
                            pass
            except Exception:
                pass

        # Si el autor del código creó un DataFrame auxiliar (p. ej. empleados_filtro)
        # y no quiso reasignar `df`, devolvemos esa tabla en `display_df` para que
        # la UI la muestre sin sobrescribir el dataset global.
        if not (isinstance(result_df, pd.DataFrame) and not result_df.empty and not result_df.equals(df.copy())):
            # Buscar DataFrames auxiliares distintos de `df` y elegir el más
            # representativo para mostrar. Priorizar variables cuyo nombre
            # contiene 'head' (p.ej. empleados_filtro_head). Si no hay, elegir
            # la DataFrame con menor número de filas (asumiendo que es la
            # porción solicitada por el usuario).
            candidates = []
            for k, v in local_ns.items():
                if k == "df" or k.startswith("_"):
                    continue
                if isinstance(v, pd.DataFrame):
                    candidates.append((k, v))

            if candidates:
                # Preferir nombre que incluya 'head'
                head_pref = next((v for (n, v) in candidates if 'head' in n.lower()), None)
                if head_pref is not None:
                    display_df = head_pref
                else:
                    # elegir dataframe con menos filas (y menor número de cols en empate)
                    def sort_key(item):
                        v = item[1]
                        try:
                            rows = int(getattr(v, 'shape', (len(v), 0))[0])
                        except Exception:
                            rows = len(v) if hasattr(v, '__len__') else 10**9
                        cols = int(getattr(v, 'shape', (0, len(v.columns) if hasattr(v, 'columns') else 0))[1]) if hasattr(v, 'shape') else 0
                        return (rows, cols)

                    candidates_sorted = sorted(candidates, key=sort_key)
                    display_df = candidates_sorted[0][1]

        # Si no se asignó `fig` explícitamente pero matplotlib generó una figura activa, se captura.
        if result_fig is None and plt.get_fignums():
            result_fig = plt.gcf()

        return ExecutionResult(
            success=True, df=result_df, fig=result_fig,
            stdout=stdout_buffer.getvalue(), display_df=display_df,
        )
    except Exception as e:
        return ExecutionResult(
            success=False, error=f"{type(e).__name__}: {e}",
            stdout=stdout_buffer.getvalue(),
        )
