from fastapi import APIRouter, Query, Request

from app.api.deps import current_session
from app.core.exceptions import AppError
from app.infra.session_store import store
from app.services.dataframe_ops import requested_column_list, resolve_columns
from app.services.eda import (
    boxplot_spec,
    build_eda_report,
    correlation_spec,
    histogram_spec,
    value_counts_table,
)

router = APIRouter(prefix="/eda", tags=["eda"])


@router.get("/report")
async def eda_report(request: Request) -> dict:
    session = store.require_df(current_session(request))
    return build_eda_report(session.df)


@router.get("/value-counts")
async def value_counts(request: Request, column: str) -> dict:
    session = store.require_df(current_session(request))
    found = resolve_columns(session.df, [column])
    if not found:
        raise AppError(f"Columna desconocida: {column}", 400)
    try:
        return value_counts_table(session.df, found[0])
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc


@router.get("/histogram")
async def histogram(
    request: Request,
    columns: list[str] | None = Query(default=None),
    column: str | None = None,
) -> dict:
    session = store.require_df(current_session(request))
    requested = requested_column_list(columns, column)
    cols = resolve_columns(session.df, requested)
    if not cols:
        split: list[str] = []
        for item in requested:
            split.extend(part for part in item.split(",") if part.strip())
        cols = resolve_columns(session.df, split)
    try:
        return {"figure": histogram_spec(session.df, cols)}
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc


@router.get("/boxplot")
async def boxplot(request: Request, columns: list[str] | None = Query(default=None)) -> dict:
    session = store.require_df(current_session(request))
    requested = requested_column_list(columns)
    try:
        return {"figure": boxplot_spec(session.df, requested)}
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc


@router.get("/correlation")
async def correlation(request: Request) -> dict:
    session = store.require_df(current_session(request))
    try:
        return {"figure": correlation_spec(session.df)}
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
