import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1 import chat, datasets, eda, ml, settings as llm_settings, wrangling
from app.core.config import settings
from app.core.exceptions import AppError
from app.infra.session_store import store

logging.getLogger("analisis_ia").setLevel(logging.INFO)

APP_DIR = Path(__file__).resolve().parent
_SECRET_FIELDS = {"api_key", "password", "user_api_key"}

app = FastAPI(title="analisis_ia", version="0.1.5")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

app.include_router(datasets.router, prefix="/api/v1")
app.include_router(eda.router, prefix="/api/v1")
app.include_router(wrangling.router, prefix="/api/v1")
app.include_router(ml.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(llm_settings.router, prefix="/api/v1")


@app.middleware("http")
async def attach_session(request: Request, call_next):
    session = store.get_or_create(request.cookies.get("analisis_session"))
    request.state.session = session
    response = await call_next(request)
    response.set_cookie("analisis_session", session.session_id, httponly=True, samesite="lax")
    return response


def _redact_validation_error(err: dict) -> dict:
    loc = err.get("loc") or ()
    names = {str(part) for part in loc}
    if names & _SECRET_FIELDS:
        scrubbed = dict(err)
        scrubbed["input"] = "[redacted]"
        if "ctx" in scrubbed:
            scrubbed["ctx"] = {}
        return scrubbed
    return err


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    detail = [_redact_validation_error(dict(row)) for row in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(detail)})


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"gemini_model": settings.gemini_model, "asset_v": app.version},
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
