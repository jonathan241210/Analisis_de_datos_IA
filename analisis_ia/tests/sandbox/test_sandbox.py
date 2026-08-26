import pandas as pd
import pytest

from app.sandbox.executor import run_generated_code
from app.sandbox.validator import UnsafeCodeError, validate_ast


def test_rejects_os_import():
    with pytest.raises(UnsafeCodeError):
        validate_ast("import os\nos.system('echo hi')")


def test_rejects_eval_name():
    with pytest.raises(UnsafeCodeError):
        validate_ast("x = eval('1+1')")


def test_rejects_open():
    with pytest.raises(UnsafeCodeError):
        validate_ast("open('secrets.txt')")


def test_allows_pandas_on_copy():
    df = pd.DataFrame({"alumno": ["ana"], "nota": [10.5]})
    result = run_generated_code("df['alumno'] = df['alumno'].str.upper()", df)
    assert result.success
    assert result.df["alumno"].iloc[0] == "ANA"
    assert df["alumno"].iloc[0] == "ana"


def test_exec_only_after_validation_blocks_subprocess():
    df = pd.DataFrame({"a": [1]})
    result = run_generated_code("import subprocess", df)
    assert result.success is False
    assert "no permitido" in (result.error or "").lower()
