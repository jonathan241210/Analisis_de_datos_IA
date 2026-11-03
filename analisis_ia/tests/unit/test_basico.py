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


def test_sandbox_runs_simple_cleaning():
    df = pd.DataFrame({"edad": [20, None, 30]})
    result = run_generated_code("df = df.dropna()", df)
    assert result.success
    assert len(result.df) == 2
