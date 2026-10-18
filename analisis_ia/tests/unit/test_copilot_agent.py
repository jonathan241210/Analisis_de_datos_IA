import json
import math

import numpy as np
import pandas as pd
import pytest

from app.services.copilot.agent_loop import run_agent_loop
from app.services.copilot.errors import MSG_GENERIC, MSG_TOKENS, classify_gemini_error
from app.services.copilot.gemini_client import ModelTurn, _generic_to_genai, _import_genai
from app.services.copilot.tools import inspect_dataset, json_safe, propose_mutations, run_python_readonly, step_label
from app.services.wrangling import apply_wrangling


def test_classify_gemini_tokens():
    assert classify_gemini_error(RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded")) == MSG_TOKENS
    assert classify_gemini_error(None, extra="rate limit exceeded") == MSG_TOKENS


def test_classify_gemini_generic():
    assert classify_gemini_error(RuntimeError("connection reset")) == MSG_GENERIC
    assert classify_gemini_error(None, extra="") == MSG_GENERIC


def test_function_results_use_user_role_for_gemini():
    _, types = _import_genai()
    contents = _generic_to_genai(
        types,
        [
            {"role": "user", "text": "analiza"},
            {"role": "model", "text": "", "calls": [{"name": "inspect_dataset", "args": {"focus": "nulls"}}]},
            {"role": "tool", "results": [{"name": "inspect_dataset", "response": {"result": {"nulls": []}}}]},
        ],
    )
    assert contents[-1].role == "user"
    assert contents[-1].parts[0].function_response.name == "inspect_dataset"
    assert contents[1].role == "model"


def test_json_safe_converts_nan_and_inf_to_none():
    cleaned = json_safe({
        "nan": float("nan"),
        "inf": float("inf"),
        "ninf": float("-inf"),
        "numpy_nan": np.nan,
        "pandas_na": pd.NA,
        "ok": 1.5,
        "nested": [{"x": math.nan}],
    })
    json.dumps(cleaned, allow_nan=False)
    assert cleaned["nan"] is None
    assert cleaned["inf"] is None
    assert cleaned["ninf"] is None
    assert cleaned["numpy_nan"] is None
    assert cleaned["pandas_na"] is None
    assert cleaned["ok"] == 1.5
    assert cleaned["nested"][0]["x"] is None


def test_inspect_dataset_head_is_strict_json_with_nulls():
    df = pd.DataFrame({
        "id": [1001, 1002],
        "sexo": ["M", "F"],
        "sexo.1": [np.nan, "F"],
    })
    payload = inspect_dataset(df, "schema")
    raw = json.dumps(payload, allow_nan=False)
    assert "NaN" not in raw
    assert payload["head"][0]["sexo.1"] is None
    assert payload["head"][0]["sexo"] == "M"


def test_inspect_nulls_dups_outliers():
    df = pd.DataFrame({
        "nota": [1.0, None, 100.0, 2.0, 2.0],
        "grupo": ["a", "a", "b", "a", "a"],
    })
    nulls = inspect_dataset(df, "nulls")
    assert nulls["nulls"][0]["column"] == "nota"
    dups = inspect_dataset(df, "duplicates")
    assert dups["duplicate_rows"] >= 1
    out = inspect_dataset(df, "outliers")
    cols = {row["column"] for row in out["outliers"]}
    assert "nota" in cols
    full = inspect_dataset(df, "all")
    assert "schema" in full and "possible_classification_targets" in full


def test_run_python_does_not_mutate_original():
    df = pd.DataFrame({"nota": [1.0, 2.0]})
    payload, extra = run_python_readonly(df, "df['nota'] = df['nota'] * 10\nprint(int(df['nota'].sum()))")
    assert payload["success"] is True
    assert payload["mutated_in_sandbox"] is True
    assert payload["applied"] is False
    assert df["nota"].tolist() == [1.0, 2.0]
    assert "10" in (payload.get("stdout") or "") or "30" in (payload.get("stdout") or "")
    assert extra.get("fig") is None


def test_run_python_payload_exposes_runtime_error_to_agent():
    df = pd.DataFrame({"a": [1]})
    payload, _extra = run_python_readonly(df, "1/0")
    assert payload["success"] is False
    assert "ZeroDivisionError" in (payload.get("error") or "")
    assert "traceback" not in (payload.get("error") or "").lower()


def test_propose_mutations_filters_unknown():
    payload, actions = propose_mutations([
        {"op": "drop_duplicates", "label": "Quitar duplicados"},
        {"op": "explode_server", "label": "nope"},
    ])
    assert payload["accepted"] == 1
    assert actions[0]["op"] == "drop_duplicates"


def test_step_label_spanish():
    assert "nulos" in step_label("inspect_dataset", {"focus": "nulls"}).lower()
    assert "Graficando" in step_label("run_python", {"purpose": "plot"})


def test_drop_duplicates_wrangling():
    df = pd.DataFrame({"a": [1, 1], "b": [2, 2]})
    out = apply_wrangling(df, "drop_duplicates")
    assert len(out) == 1


@pytest.mark.asyncio
async def test_agent_loop_uses_inspect_then_replies():
    df = pd.DataFrame({"nota": [1.0, None, 3.0]})
    n = {"i": 0}

    async def ask(_contents):
        n["i"] += 1
        if n["i"] == 1:
            return ModelTurn(calls=[{"name": "inspect_dataset", "args": {"focus": "nulls"}}])
        return ModelTurn(text="Hay nulos en nota. Para ML conviene imputar antes.")

    events = []
    async for ev in run_agent_loop(df, "analiza el dataset", [], "eda", ask=ask):
        events.append(ev)
    types = [e["type"] for e in events]
    assert "step" in types
    assert any(e.get("label", "").lower().find("nulos") >= 0 for e in events if e["type"] == "step")
    final = [e for e in events if e["type"] == "final"][-1]
    assert "nulos" in final["content"].lower()
    assert n["i"] == 2


@pytest.mark.asyncio
async def test_agent_loop_step_includes_summary_when_provided():
    df = pd.DataFrame({"nota": [1.0, None, 3.0]})
    n = {"i": 0}

    async def ask(_contents):
        n["i"] += 1
        if n["i"] == 1:
            return ModelTurn(
                calls=[
                    {
                        "name": "inspect_dataset",
                        "args": {"focus": "nulls", "summary": "Revisando cuántos valores nulos tiene el dataset."},
                    }
                ]
            )
        return ModelTurn(text="Hay nulos en nota.")

    events = []
    async for ev in run_agent_loop(df, "analiza el dataset", [], "eda", ask=ask):
        events.append(ev)
    tool_steps = [e for e in events if e["type"] == "step" and e.get("id") == "t1"]
    assert tool_steps, "expected a step event for the dispatched tool call"
    for step in tool_steps:
        assert step.get("summary") == "Revisando cuántos valores nulos tiene el dataset."


@pytest.mark.asyncio
async def test_agent_loop_step_omits_summary_when_missing():
    df = pd.DataFrame({"nota": [1.0, None, 3.0]})
    n = {"i": 0}

    async def ask(_contents):
        n["i"] += 1
        if n["i"] == 1:
            return ModelTurn(calls=[{"name": "inspect_dataset", "args": {"focus": "nulls"}}])
        return ModelTurn(text="Hay nulos en nota.")

    events = []
    async for ev in run_agent_loop(df, "analiza el dataset", [], "eda", ask=ask):
        events.append(ev)
    tool_steps = [e for e in events if e["type"] == "step" and e.get("id") == "t1"]
    assert tool_steps
    for step in tool_steps:
        assert not step.get("summary")
        assert step.get("label")
