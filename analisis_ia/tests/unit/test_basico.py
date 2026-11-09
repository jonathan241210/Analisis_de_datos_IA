"""Simple smoke tests used by the CI pipeline (GitHub Actions build activity)."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sandbox.executor import run_generated_code
from app.sandbox.extract import extract_python_code
from app.sandbox.validator import UnsafeCodeError, validate_ast


def test_health_endpoint_ok():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_extract_python_code_block():
    text = "Texto\n```python\nprint('hola')\n```\nfin"
    assert extract_python_code(text) == ["print('hola')"]


def test_sandbox_blocks_subprocess():
    with pytest.raises(UnsafeCodeError):
        validate_ast("import subprocess")


def test_sandbox_blocks_os_import():
    with pytest.raises(UnsafeCodeError):
        validate_ast("import os")


def test_extract_python_code_without_block_returns_empty():
    assert extract_python_code("Solo texto, sin codigo") == []


@pytest.mark.parametrize(
    "code",
    [
        "import sys",
        "import subprocess",
        "__import__('os').system('ls')",
        "eval('1 + 1')",
        "open('/etc/passwd').read()",
    ],
)
def test_sandbox_rejects_dangerous_snippets(code):
    with pytest.raises(UnsafeCodeError):
        validate_ast(code)


def test_sandbox_runs_multi_step_cleaning_pipeline():
    df = pd.DataFrame(
        {
            "ciudad": ["Lima", "Lima", "Quito", "Quito", "Bogota", None],
            "ventas": [100.0, 100.0, None, 250.0, 300.0, 50.0],
        }
    )
    code = (
        "df = df.drop_duplicates()\n"
        "df = df.dropna(subset=['ciudad'])\n"
        "df['ventas'] = df.groupby('ciudad')['ventas'].transform(lambda s: s.fillna(s.mean()))\n"
        "df['ventas'] = df['ventas'].fillna(df['ventas'].median())\n"
        "df = df.sort_values('ventas', ascending=False).reset_index(drop=True)\n"
    )
    result = run_generated_code(code, df)
    assert result.success
    assert len(result.df) == 4
    assert result.df["ventas"].isna().sum() == 0
    assert result.df["ventas"].is_monotonic_decreasing
    assert result.df.loc[0, "ciudad"] == "Bogota"


def test_sandbox_runs_simple_cleaning():
    df = pd.DataFrame({"edad": [20, None, 30]})
    result = run_generated_code("df = df.dropna()", df)
    assert result.success
    assert len(result.df) == 2
