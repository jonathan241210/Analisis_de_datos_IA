from __future__ import annotations

MSG_TOKENS = "Se acabaron los tokens"
MSG_GENERIC = "Error al generar respuesta"

_TOKEN_MARKERS = (
    "resource_exhausted",
    "resource exhausted",
    "quota exceeded",
    "quota_exceeded",
    "insufficient_quota",
    "exceeded your current quota",
    "rate limit",
    "rate_limit",
    "ratelimit",
    "tokens exhausted",
    "token quota",
    "out of tokens",
    "no remaining tokens",
    "billing",
)


def _blob(exc: BaseException | None, extra: str = "") -> str:
    bits = [extra, str(exc or "")]
    if exc is not None:
        for attr in ("status_code", "code", "status", "message"):
            bits.append(str(getattr(exc, attr, "") or ""))
        cause = getattr(exc, "__cause__", None)
        if cause is not None and cause is not exc:
            bits.append(str(cause))
    return " ".join(bits).lower()


def classify_gemini_error(exc: BaseException | None = None, extra: str = "") -> str:
    """Map Gemini/SDK failures to the two user-safe Spanish lines."""
    text = _blob(exc, extra)
    if "429" in text or any(m in text for m in _TOKEN_MARKERS):
        return MSG_TOKENS
    return MSG_GENERIC
