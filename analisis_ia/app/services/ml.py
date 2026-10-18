import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from app.core.exceptions import AppError
from app.services.plotly_json import fig_to_dict

try:
    from xgboost import XGBClassifier, XGBRegressor

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

CLASSIFIERS = {
    "Regresión Logística": LogisticRegression,
    "Random Forest": RandomForestClassifier,
    "Decision Tree": DecisionTreeClassifier,
}
REGRESSORS = {
    "Regresión Lineal": LinearRegression,
    "Random Forest": RandomForestRegressor,
    "Decision Tree": DecisionTreeRegressor,
}
if XGBOOST_AVAILABLE:
    CLASSIFIERS["XGBoost"] = XGBClassifier
    REGRESSORS["XGBoost"] = XGBRegressor


def suggested_task(df: pd.DataFrame, target: str) -> str:
    series = df[target]
    if series.dtype == "object" or series.dtype.name == "category" or series.nunique() <= 15:
        return "Clasificación"
    return "Regresión"


def train_supervised(
    df: pd.DataFrame,
    target: str,
    features: list[str],
    task_type: str,
    algo_name: str,
    test_size: float = 0.2,
) -> dict:
    if not features:
        raise AppError("Selecciona al menos una variable predictora.", 400)
    if target not in df.columns:
        raise AppError("Variable objetivo inválida.", 400)

    X = pd.get_dummies(df[features], drop_first=True)
    y = df[target]
    if X.isnull().any().any() or y.isnull().any():
        raise AppError("Hay nulos en X o Y. Limpia los datos antes de entrenar.", 400)

    algo_dict = CLASSIFIERS if task_type == "Clasificación" else REGRESSORS
    if algo_name not in algo_dict:
        raise AppError(f"Algoritmo no disponible: {algo_name}", 400)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
    model = algo_dict[algo_name]()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    result: dict = {"task_type": task_type, "algorithm": algo_name, "xgboost": XGBOOST_AVAILABLE}
    figures: list[dict] = []

    if task_type == "Clasificación":
        result["accuracy"] = float(accuracy_score(y_test, y_pred))
        result["f1_weighted"] = float(f1_score(y_test, y_pred, average="weighted"))
        cm = confusion_matrix(y_test, y_pred)
        fig = px.imshow(
            cm, text_auto=True, color_continuous_scale="Blues",
            labels={"x": "Predicho", "y": "Real", "color": "Conteo"},
            title="Matriz de Confusión",
        )
        figures.append(fig_to_dict(fig))
    else:
        result["mse"] = float(mean_squared_error(y_test, y_pred))
        result["r2"] = float(r2_score(y_test, y_pred))
        fig = px.scatter(x=y_test, y=y_pred, labels={"x": "Real", "y": "Predicho"}, title="Reales vs. Predichos")
        fig.add_shape(
            type="line",
            x0=float(np.min(y_test)), y0=float(np.min(y_test)),
            x1=float(np.max(y_test)), y1=float(np.max(y_test)),
            line={"dash": "dash"},
        )
        figures.append(fig_to_dict(fig))

    if hasattr(model, "feature_importances_"):
        imp_df = pd.DataFrame({
            "feature": X.columns,
            "importancia": model.feature_importances_,
        }).sort_values("importancia", ascending=False).head(15)
        fig_imp = px.bar(imp_df, x="importancia", y="feature", orientation="h", title="Importancia de variables")
        figures.append(fig_to_dict(fig_imp))

    result["figures"] = figures
    return result


def unsupervised(df: pd.DataFrame, features: list[str], method: str, **kwargs) -> dict:
    if len(features) < 2:
        raise AppError("Selecciona al menos 2 columnas numéricas.", 400)
    X = df[features].dropna()
    if method == "elbow":
        max_k = int(kwargs.get("max_k", 10))
        inertias = []
        ks = list(range(2, max_k + 1))
        for k in ks:
            km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
            inertias.append(float(km.inertia_))
        fig = px.line(x=ks, y=inertias, markers=True, labels={"x": "K", "y": "Inercia"}, title="Método del codo")
        return {"method": "elbow", "inertias": inertias, "figures": [fig_to_dict(fig)]}

    if method == "kmeans":
        k = int(kwargs.get("k", 3))
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)
        plot_df = X.copy()
        plot_df["cluster"] = labels.astype(str)
        fig = px.scatter_matrix(plot_df, dimensions=features[:4], color="cluster", title="Clusters K-Means")
        return {"method": "kmeans", "k": k, "figures": [fig_to_dict(fig)]}

    if method == "dbscan":
        eps = float(kwargs.get("eps", 0.5))
        min_samples = int(kwargs.get("min_samples", 5))
        labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)
        plot_df = X.copy()
        plot_df["cluster"] = labels.astype(str)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        fig = px.scatter_matrix(plot_df, dimensions=features[:4], color="cluster", title="Clusters DBSCAN")
        return {
            "method": "dbscan",
            "n_clusters": n_clusters,
            "figures": [fig_to_dict(fig)],
        }

    if method == "pca":
        n_components = int(kwargs.get("n_components", 2))
        pca = PCA(n_components=n_components, random_state=42)
        components = pca.fit_transform(X)
        var_explained = float(pca.explained_variance_ratio_.sum())
        if n_components == 2:
            fig = px.scatter(x=components[:, 0], y=components[:, 1], labels={"x": "PC1", "y": "PC2"}, title="PCA 2D")
        else:
            fig = px.scatter_3d(
                x=components[:, 0], y=components[:, 1], z=components[:, 2],
                labels={"x": "PC1", "y": "PC2", "z": "PC3"}, title="PCA 3D",
            )
        return {"method": "pca", "variance_explained": var_explained, "figures": [fig_to_dict(fig)]}

    raise AppError(f"Método no soportado: {method}", 400)
