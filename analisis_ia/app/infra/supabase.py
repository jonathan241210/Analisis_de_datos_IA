"""Placeholder for future Supabase Auth / Storage / Postgres wiring."""


def supabase_configured(url: str, anon_key: str) -> bool:
    return bool(url and anon_key)
