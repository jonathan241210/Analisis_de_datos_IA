import ast
import re

FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "exit", "quit", "help", "breakpoint",
}

ALLOWED_IMPORT_MODULES = {
    "pandas", "numpy", "matplotlib", "matplotlib.pyplot", "seaborn",
    "plotly", "plotly.express", "plotly.graph_objects", "sklearn",
    "scipy", "scipy.stats",
}

FORBIDDEN_MODULE_PATTERNS = re.compile(
    r"^(os|sys|subprocess|shutil|socket|pathlib|requests|urllib|http|"
    r"pickle|importlib|ctypes|multiprocessing|threading)(\.|$)"
)


class UnsafeCodeError(Exception):
    pass


def _attr_chain(node: ast.Attribute) -> str:
    parts = [node.attr]
    cur = node.value
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def validate_ast(code: str) -> ast.AST:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise UnsafeCodeError(f"Error de sintaxis en el código generado: {exc}") from exc

    for node in ast.walk(tree):
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

    return tree
