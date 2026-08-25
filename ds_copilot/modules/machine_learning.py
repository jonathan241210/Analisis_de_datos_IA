"""
modules/machine_learning.py
Módulo 4: Machine Learning (Supervisado y No Supervisado).
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, mean_squared_error, r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from utils.helpers import numeric_columns

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


def _supervised(df: pd.DataFrame):
    st.markdown("### 🎯 Aprendizaje Supervisado")
    all_cols = df.columns.tolist()

    target = st.selectbox("Variable objetivo (Y)", all_cols, key="ml_target")
    feature_options = [c for c in all_cols if c != target]
    features = st.multiselect(
        "Variables predictoras (X)", feature_options, default=feature_options, key="ml_features"
    )

    if not features:
        st.info("Selecciona al menos una variable predictora.")
        return

    is_classification = (
        df[target].dtype == "object"
        or df[target].dtype.name == "category"
        or df[target].nunique() <= 15
    )
    task_type = st.radio(
        "Tipo de problema",
        ["Clasificación", "Regresión"],
        index=0 if is_classification else 1,
        horizontal=True,
        key="ml_task_type",
    )

    algo_dict = CLASSIFIERS if task_type == "Clasificación" else REGRESSORS
    algo_name = st.selectbox("Algoritmo", list(algo_dict.keys()), key="ml_algo")
    test_size = st.slider("Proporción de test", 0.1, 0.5, 0.2, 0.05, key="ml_test_size")

    if st.button("🚀 Entrenar modelo", key="ml_train_btn"):
        try:
            X = pd.get_dummies(df[features], drop_first=True)
            y = df[target]

            if X.isnull().any().any() or y.isnull().any():
                st.error("Hay valores nulos en X o Y. Limpia los datos en el módulo de Wrangling antes de entrenar.")
                return

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )

            model = algo_dict[algo_name]()
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            st.markdown("#### 📋 Resultados")
            if task_type == "Clasificación":
                acc = accuracy_score(y_test, y_pred)
                f1 = f1_score(y_test, y_pred, average="weighted")
                c1, c2 = st.columns(2)
                c1.metric("Accuracy", f"{acc:.4f}")
                c2.metric("F1-Score (weighted)", f"{f1:.4f}")

                cm = confusion_matrix(y_test, y_pred)
                fig = px.imshow(
                    cm, text_auto=True, color_continuous_scale="Blues",
                    labels=dict(x="Predicho", y="Real", color="Conteo"),
                    title="Matriz de Confusión",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                c1, c2 = st.columns(2)
                c1.metric("MSE", f"{mse:.4f}")
                c2.metric("R²", f"{r2:.4f}")

                fig = px.scatter(
                    x=y_test, y=y_pred, labels={"x": "Real", "y": "Predicho"},
                    title="Valores Reales vs. Predichos",
                )
                fig.add_shape(
                    type="line", x0=y_test.min(), y0=y_test.min(),
                    x1=y_test.max(), y1=y_test.max(), line=dict(dash="dash"),
                )
                st.plotly_chart(fig, use_container_width=True)

            if hasattr(model, "feature_importances_"):
                imp_df = pd.DataFrame({
                    "feature": X.columns, "importancia": model.feature_importances_,
                }).sort_values("importancia", ascending=False).head(15)
                fig_imp = px.bar(imp_df, x="importancia", y="feature", orientation="h",
                                  title="Importancia de variables")
                st.plotly_chart(fig_imp, use_container_width=True)

        except Exception as e:
            st.error(f"Error al entrenar el modelo: {e}")


def _unsupervised(df: pd.DataFrame):
    st.markdown("### 🧩 Aprendizaje No Supervisado")
    num_cols = numeric_columns(df)
    if len(num_cols) < 2:
        st.info("Se necesitan al menos 2 columnas numéricas.")
        return

    features = st.multiselect(
        "Columnas numéricas a usar", num_cols, default=num_cols[: min(6, len(num_cols))],
        key="ml_unsup_features",
    )
    if len(features) < 2:
        st.info("Selecciona al menos 2 columnas.")
        return

    X = df[features].dropna()
    tab1, tab2, tab3 = st.tabs(["K-Means (método del codo)", "DBSCAN", "PCA (2D/3D)"])

    with tab1:
        max_k = st.slider("K máximo para método del codo", 2, 15, 10, key="ml_kmeans_maxk")
        if st.button("Calcular método del codo", key="ml_elbow_btn"):
            inertias = []
            for k in range(2, max_k + 1):
                km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
                inertias.append(km.inertia_)
            fig = px.line(x=list(range(2, max_k + 1)), y=inertias, markers=True,
                           labels={"x": "K (clusters)", "y": "Inercia"},
                           title="Método del codo")
            st.plotly_chart(fig, use_container_width=True)

        k_final = st.number_input("K final para clustering", 2, 20, 3, key="ml_kmeans_k")
        if st.button("Ejecutar K-Means", key="ml_kmeans_btn"):
            km = KMeans(n_clusters=k_final, random_state=42, n_init=10)
            labels = km.fit_predict(X)
            plot_df = X.copy()
            plot_df["cluster"] = labels.astype(str)
            fig = px.scatter_matrix(plot_df, dimensions=features[:4], color="cluster",
                                     title="Clusters K-Means")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        eps = st.slider("eps", 0.1, 5.0, 0.5, 0.1, key="ml_dbscan_eps")
        min_samples = st.slider("min_samples", 2, 20, 5, key="ml_dbscan_min")
        if st.button("Ejecutar DBSCAN", key="ml_dbscan_btn"):
            db = DBSCAN(eps=eps, min_samples=min_samples)
            labels = db.fit_predict(X)
            plot_df = X.copy()
            plot_df["cluster"] = labels.astype(str)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            st.write(f"Clusters detectados: **{n_clusters}** (−1 = ruido)")
            fig = px.scatter_matrix(plot_df, dimensions=features[:4], color="cluster",
                                     title="Clusters DBSCAN")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        n_components = st.radio("Dimensiones", [2, 3], horizontal=True, key="ml_pca_dim")
        if st.button("Ejecutar PCA", key="ml_pca_btn"):
            pca = PCA(n_components=n_components, random_state=42)
            components = pca.fit_transform(X)
            var_explained = pca.explained_variance_ratio_.sum()
            st.write(f"Varianza explicada: **{var_explained:.2%}**")
            if n_components == 2:
                fig = px.scatter(x=components[:, 0], y=components[:, 1],
                                  labels={"x": "PC1", "y": "PC2"}, title="PCA 2D")
            else:
                fig = px.scatter_3d(
                    x=components[:, 0], y=components[:, 1], z=components[:, 2],
                    labels={"x": "PC1", "y": "PC2", "z": "PC3"}, title="PCA 3D",
                )
            st.plotly_chart(fig, use_container_width=True)


def render():
    st.subheader("🤖 Machine Learning")
    df = st.session_state.get("df")
    if df is None:
        st.warning("Primero carga un dataset en el módulo de Ingesta de Datos.")
        return
    if not XGBOOST_AVAILABLE:
        st.caption("ℹ️ XGBoost no está instalado — ese algoritmo no aparecerá en la lista. `pip install xgboost` para habilitarlo.")

    mode = st.radio("Modo", ["Supervisado", "No Supervisado"], horizontal=True, key="ml_mode")
    st.divider()
    if mode == "Supervisado":
        _supervised(df)
    else:
        _unsupervised(df)
