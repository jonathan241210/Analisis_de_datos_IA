from fastapi import APIRouter, Request

from app.api.deps import current_session
from app.infra.session_store import store
from app.schemas.payloads import SupervisedRequest, UnsupervisedRequest
from app.services.dataframe_ops import numeric_columns
from app.services.ml import CLASSIFIERS, REGRESSORS, suggested_task, train_supervised, unsupervised, XGBOOST_AVAILABLE

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/options")
async def options(request: Request) -> dict:
    session = store.require_df(current_session(request))
    df = session.df
    return {
        "columns": list(df.columns),
        "numeric_columns": numeric_columns(df),
        "classifiers": list(CLASSIFIERS.keys()),
        "regressors": list(REGRESSORS.keys()),
        "xgboost": XGBOOST_AVAILABLE,
        "suggested": {c: suggested_task(df, c) for c in df.columns},
    }


@router.post("/supervised")
async def supervised(request: Request, body: SupervisedRequest) -> dict:
    session = store.require_df(current_session(request))
    return train_supervised(
        session.df, body.target, body.features, body.task_type, body.algorithm, body.test_size,
    )


@router.post("/unsupervised")
async def unsup(request: Request, body: UnsupervisedRequest) -> dict:
    session = store.require_df(current_session(request))
    return unsupervised(
        session.df,
        body.features,
        body.method,
        max_k=body.max_k,
        k=body.k,
        eps=body.eps,
        min_samples=body.min_samples,
        n_components=body.n_components,
    )
