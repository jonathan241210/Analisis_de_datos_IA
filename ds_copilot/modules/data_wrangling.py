"""
modules/data_wrangling.py
Módulo 3: Limpieza y Transformación (Data Wrangling).
"""
import pandas as pd
import streamlit as st
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder

from utils.session_state import update_dataframe, undo_last_transformation
from utils.helpers import numeric_columns, categorical_columns, df_to_csv_bytes


def _nulls_and_duplicates(df: pd.DataFrame):
    st.markdown("### 🧹 Nulos y Duplicados")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Imputación de nulos**")
        target_cols = st.multiselect(
            "Columnas a imputar", df.columns.tolist(), key="wr_impute_cols"
        )
        strategy = st.selectbox(
            "Estrategia", ["Media", "Mediana", "Moda", "Constante", "Eliminar filas"],
            key="wr_impute_strategy",
        )
        constant_value = None
        if strategy == "Constante":
            constant_value = st.text_input("Valor constante", key="wr_impute_constant")

        if st.button("Aplicar imputación", key="wr_apply_impute"):
            new_df = df.copy()
            if strategy == "Eliminar filas":
                new_df = new_df.dropna(subset=target_cols if target_cols else None)
            else:
                for c in target_cols:
                    if strategy == "Media" and pd.api.types.is_numeric_dtype(new_df[c]):
                        new_df[c] = new_df[c].fillna(new_df[c].mean())
                    elif strategy == "Mediana" and pd.api.types.is_numeric_dtype(new_df[c]):
                        new_df[c] = new_df[c].fillna(new_df[c].median())
                    elif strategy == "Moda":
                        mode = new_df[c].mode(dropna=True)
                        if not mode.empty:
                            new_df[c] = new_df[c].fillna(mode.iloc[0])
                    elif strategy == "Constante":
                        new_df[c] = new_df[c].fillna(constant_value)
            update_dataframe(new_df)
            st.success("Imputación aplicada.")
            st.rerun()

    with col2:
        st.markdown("**Duplicados**")
        n_dup = int(df.duplicated().sum())
        st.write(f"Filas duplicadas detectadas: **{n_dup}**")
        if st.button("Eliminar duplicados", key="wr_drop_dup", disabled=n_dup == 0):
            update_dataframe(df.drop_duplicates().reset_index(drop=True))
            st.success("Duplicados eliminados.")
            st.rerun()


def _type_casting(df: pd.DataFrame):
    st.markdown("### 🔤 Casteo y Tipado")
    col = st.selectbox("Columna a convertir", df.columns.tolist(), key="wr_cast_col")
    target_type = st.selectbox(
        "Tipo destino", ["string", "numeric", "datetime", "category"], key="wr_cast_type"
    )
    if st.button("Convertir tipo", key="wr_apply_cast"):
        new_df = df.copy()
        try:
            if target_type == "string":
                new_df[col] = new_df[col].astype(str)
            elif target_type == "numeric":
                new_df[col] = pd.to_numeric(new_df[col], errors="coerce")
            elif target_type == "datetime":
                new_df[col] = pd.to_datetime(new_df[col], errors="coerce")
            elif target_type == "category":
                new_df[col] = new_df[col].astype("category")
            update_dataframe(new_df)
            st.success(f"Columna '{col}' convertida a {target_type}.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al convertir: {e}")


def _feature_engineering(df: pd.DataFrame):
    st.markdown("### ⚙️ Feature Engineering")
    tab1, tab2, tab3 = st.tabs(["Escalado", "Codificación", "Renombrar / Filtrar"])

    with tab1:
        num_cols = numeric_columns(df)
        cols = st.multiselect("Columnas numéricas a escalar", num_cols, key="wr_scale_cols")
        method = st.radio("Método", ["StandardScaler", "MinMaxScaler"], horizontal=True, key="wr_scale_method")
        if st.button("Aplicar escalado", key="wr_apply_scale", disabled=not cols):
            new_df = df.copy()
            scaler = StandardScaler() if method == "StandardScaler" else MinMaxScaler()
            new_df[cols] = scaler.fit_transform(new_df[cols])
            update_dataframe(new_df)
            st.success(f"Escalado {method} aplicado a {len(cols)} columna(s).")
            st.rerun()

    with tab2:
        cat_cols = categorical_columns(df)
        cols = st.multiselect("Columnas categóricas a codificar", cat_cols, key="wr_encode_cols")
        method = st.radio("Método", ["One-Hot Encoding", "Label Encoding"], horizontal=True, key="wr_encode_method")
        if st.button("Aplicar codificación", key="wr_apply_encode", disabled=not cols):
            new_df = df.copy()
            if method == "One-Hot Encoding":
                new_df = pd.get_dummies(new_df, columns=cols, drop_first=False)
            else:
                for c in cols:
                    new_df[c] = LabelEncoder().fit_transform(new_df[c].astype(str))
            update_dataframe(new_df)
            st.success(f"Codificación {method} aplicada.")
            st.rerun()

    with tab3:
        rc1, rc2 = st.columns(2)
        with rc1:
            old_name = st.selectbox("Columna a renombrar", df.columns.tolist(), key="wr_rename_old")
            new_name = st.text_input("Nuevo nombre", key="wr_rename_new")
            if st.button("Renombrar", key="wr_apply_rename", disabled=not new_name):
                update_dataframe(df.rename(columns={old_name: new_name}))
                st.success("Columna renombrada.")
                st.rerun()
        with rc2:
            drop_cols = st.multiselect("Columnas a eliminar", df.columns.tolist(), key="wr_drop_cols")
            if st.button("Eliminar columnas", key="wr_apply_drop", disabled=not drop_cols):
                update_dataframe(df.drop(columns=drop_cols))
                st.success("Columnas eliminadas.")
                st.rerun()


def _export(df: pd.DataFrame):
    st.markdown("### 💾 Exportación")
    st.download_button(
        "⬇️ Descargar dataset transformado (CSV)",
        data=df_to_csv_bytes(df),
        file_name="dataset_transformado.csv",
        mime="text/csv",
    )


def render():
    st.subheader("🧰 Limpieza y Transformación (Data Wrangling)")
    df = st.session_state.get("df")
    if df is None:
        st.warning("Primero carga un dataset en el módulo de Ingesta de Datos.")
        return

    top_c1, top_c2 = st.columns([1, 5])
    with top_c1:
        if st.button("↩️ Deshacer última operación"):
            if undo_last_transformation():
                st.success("Se deshizo la última transformación.")
                st.rerun()
            else:
                st.info("No hay operaciones para deshacer.")

    st.dataframe(df.head(10), use_container_width=True)
    st.divider()

    _nulls_and_duplicates(df)
    st.divider()
    _type_casting(df)
    st.divider()
    _feature_engineering(df)
    st.divider()
    _export(df)
