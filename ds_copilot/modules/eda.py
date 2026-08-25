"""
modules/eda.py
Módulo 2: Análisis Exploratorio y Descriptivo (EDA).
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.helpers import human_readable_bytes, numeric_columns, zero_variance_columns, categorical_columns


def _general_metrics(df: pd.DataFrame):
    st.markdown("### 📐 Métricas Generales")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas × Columnas", f"{df.shape[0]:,} × {df.shape[1]:,}")
    c2.metric("Memoria total", human_readable_bytes(df.memory_usage(deep=True).sum()))
    c3.metric("Filas duplicadas", int(df.duplicated().sum()))
    c4.metric("Columnas varianza cero", len(zero_variance_columns(df)))

    with st.expander("Tipos de datos por columna (dtypes)"):
        dtypes_df = pd.DataFrame({
            "columna": df.dtypes.index,
            "tipo": df.dtypes.values.astype(str),
        })
        st.dataframe(dtypes_df, use_container_width=True, hide_index=True)


def _descriptive_stats(df: pd.DataFrame):
    st.markdown("### 📊 Estadística Descriptiva")
    num_cols = numeric_columns(df)
    if num_cols:
        st.dataframe(df[num_cols].describe().T, use_container_width=True)
    else:
        st.info("No hay columnas numéricas para describir.")

    # Resumen para columnas categóricas: nunique y top N valores
    cat_cols = categorical_columns(df)
    if cat_cols:
        rows = []
        for c in cat_cols:
            vc = df[c].value_counts(dropna=False)
            top = ", ".join(f"{i}={v}" for i, v in vc.head(5).items())
            rows.append({"columna": c, "n_unique": int(df[c].nunique(dropna=False)), "top_values": top})
        cat_df = pd.DataFrame(rows)
        st.markdown("#### 🧾 Resumen categórico (nunique + top values)")
        st.dataframe(cat_df, use_container_width=True)

        # Selector para explorar una columna categórica en detalle
        sel = st.selectbox("Explorar columna categórica", [None] + cat_cols, key="eda_cat_sel")
        if sel:
            vc = df[sel].value_counts(dropna=False).reset_index()
            vc.columns = [sel, "count"]
            st.dataframe(vc, use_container_width=True)


def _quality_diagnosis(df: pd.DataFrame):
    st.markdown("### 🔍 Diagnóstico de Calidad")
    nulls = df.isnull().sum()
    pct = (nulls / len(df) * 100).round(2) if len(df) else nulls
    quality_df = pd.DataFrame({
        "columna": df.columns,
        "nulos": nulls.values,
        "% nulos": pct.values,
        "tipo": df.dtypes.values.astype(str),
    }).sort_values("nulos", ascending=False)
    st.dataframe(quality_df, use_container_width=True, hide_index=True)

    zero_var = zero_variance_columns(df)
    if zero_var:
        st.warning(f"Columnas con varianza cero: {', '.join(zero_var)}")


def _visualizations(df: pd.DataFrame):
    st.markdown("### 📈 Visualización Automática")
    num_cols = numeric_columns(df)

    if not num_cols:
        st.info("No hay columnas numéricas para graficar.")
        return

    tab1, tab2, tab3 = st.tabs(["Histogramas", "Boxplots (outliers)", "Matriz de correlación"])

    with tab1:
        col = st.selectbox("Columna para histograma", num_cols, key="eda_hist_col")
        fig = px.histogram(df, x=col, nbins=40, title=f"Distribución de {col}")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        selected = st.multiselect(
            "Columnas para boxplot", num_cols, default=num_cols[: min(5, len(num_cols))]
        )
        if selected:
            fig = px.box(df[selected], title="Boxplots — detección de atípicos")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        if len(num_cols) >= 2:
            corr = df[num_cols].corr(numeric_only=True)
            fig = px.imshow(
                corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r",
                title="Matriz de correlación",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Se necesitan al menos 2 columnas numéricas para la matriz de correlación.")


def render():
    st.subheader("🔬 Análisis Exploratorio y Descriptivo (EDA)")
    df = st.session_state.get("df")
    if df is None:
        st.warning("Primero carga un dataset en el módulo de Ingesta de Datos.")
        return

    _general_metrics(df)
    st.divider()
    _descriptive_stats(df)
    st.divider()
    _quality_diagnosis(df)
    st.divider()
    _visualizations(df)
