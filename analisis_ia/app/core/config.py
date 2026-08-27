from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ANALISIS_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ANALISIS_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    gemini_model: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    n_head_rows: int = 3
    n_sample_rows: int = 3
    n_top_categories: int = 5
    max_columns_in_metadata: int = 60
    undo_limit: int = 15
    sandbox_timeout_s: float = 30.0
    preview_rows: int = 20


settings = Settings()
