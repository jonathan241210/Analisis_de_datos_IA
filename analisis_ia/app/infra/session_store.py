from __future__ import annotations

from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import AppError
from app.domain.models import AnalysisSession


class SessionStore:
    """In-memory sessions. Supabase Storage can replace this later."""

    def __init__(self) -> None:
        self._sessions: dict[str, AnalysisSession] = {}

    def get_or_create(self, session_id: str | None) -> AnalysisSession:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        new_id = session_id or uuid4().hex
        session = AnalysisSession(session_id=new_id)
        self._sessions[new_id] = session
        return session

    def require_df(self, session: AnalysisSession) -> AnalysisSession:
        if session.df is None:
            raise AppError("No hay un dataset cargado. Sube un archivo primero.", 400)
        return session

    def set_dataframe(self, session: AnalysisSession, df, file_name: str, meta: dict | None = None) -> None:
        session.df = df
        session.df_original = df.copy()
        session.file_name = file_name
        session.history = []
        session.ingest_meta = meta or {}

    def push_and_set(self, session: AnalysisSession, new_df) -> None:
        if session.df is not None:
            session.history.append(session.df.copy())
            session.history = session.history[-settings.undo_limit :]
        session.df = new_df

    def undo(self, session: AnalysisSession) -> bool:
        if not session.history:
            return False
        session.df = session.history.pop()
        return True


store = SessionStore()
