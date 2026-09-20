from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ExecutionResult:
    success: bool
    df: pd.DataFrame | None = None
    display_df: pd.DataFrame | None = None
    fig: dict | None = None
    stdout: str = ""
    error: str | None = None
    detail: str | None = None


@dataclass
class AnalysisSession:
    session_id: str
    file_name: str | None = None
    df: pd.DataFrame | None = None
    df_original: pd.DataFrame | None = None
    history: list[pd.DataFrame] = field(default_factory=list)
    chat_history: list[dict[str, str]] = field(default_factory=list)
    ingest_meta: dict[str, str] = field(default_factory=dict)
    llm_active_id: str = "gemini"
    llm_slots: dict[str, dict[str, str]] = field(default_factory=dict)
    llm_last_fallback: dict[str, Any] | None = None
