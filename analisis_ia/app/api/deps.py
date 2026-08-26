from fastapi import Request

from app.domain.models import AnalysisSession
from app.infra.session_store import store


def current_session(request: Request) -> AnalysisSession:
    return request.state.session
