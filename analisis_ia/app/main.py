import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1 import chat, datasets, eda, ml, wrangling
from app.core.config import settings
from app.core.exceptions import AppError
from app.infra.session_store import store

logging.getLogger("analisis_ia").setLevel(logging.INFO)

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="analisis_ia", version="0.1.4")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

app.include_router(datasets.router, prefix="/api/v1")
app.include_router(eda.router, prefix="/api/v1")
app.include_router(wrangling.router, prefix="/api/v1")
app.include_router(ml.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


@app.middleware("http")
async def attach_session(request: Request, call_next):
    session = store.get_or_create(request.cookies.get("analisis_session"))
    request.state.session = session
    response = await call_next(request)
    response.set_cookie("analisis_session", session.session_id, httponly=True, samesite="lax")
    return response


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


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
