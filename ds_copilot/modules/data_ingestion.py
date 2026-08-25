"""
modules/data_ingestion.py
Módulo 1: Carga e Ingesta de Datos.
Interfaz drag-and-drop para CSV / Excel / TSV con vista previa inmediata.
"""
import chardet
import pandas as pd
import streamlit as st

from utils.session_state import set_dataframe
from utils.helpers import human_readable_bytes


def _detect_encoding(raw_bytes: bytes) -> str:
    result = chardet.detect(raw_bytes[:200_000])
    return result.get("encoding") or "utf-8"


def _read_file(uploaded_file) -> tuple[pd.DataFrame, dict]:
    """Lee el archivo subido detectando formato, separador y codificación."""
    name = uploaded_file.name.lower()
    meta = {"file_name": uploaded_file.name}

    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
        meta["formato"] = "Excel"
        meta["encoding"] = "N/A (binario)"
        meta["separador"] = "N/A"
        return df, meta

    raw_bytes = uploaded_file.getvalue()
    encoding = _detect_encoding(raw_bytes)
    text_sample = raw_bytes[:5000].decode(encoding, errors="replace")

    separator = "\t" if name.endswith(".tsv") else _sniff_separator(text_sample)

    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, sep=separator, encoding=encoding)

    meta["formato"] = "TSV" if name.endswith(".tsv") else "CSV"
    meta["encoding"] = encoding
    meta["separador"] = repr(separator)
    return df, meta


def _sniff_separator(sample_text: str) -> str:
    candidates = [",", ";", "\t", "|"]
    counts = {c: sample_text.count(c) for c in candidates}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def render():
    st.subheader("📥 Carga e Ingesta de Datos")
    st.caption("Arrastra un archivo CSV, TSV o Excel (.xlsx) para comenzar.")

    uploaded_file = st.file_uploader(
        "Suelta tu archivo aquí",
        type=["csv", "tsv", "xlsx", "xls"],
        accept_multiple_files=False,
    )

    if uploaded_file is not None:
        try:
            with st.spinner("Leyendo y perfilando el archivo..."):
                df, meta = _read_file(uploaded_file)
            set_dataframe(df, file_name=meta["file_name"])
            st.success(f"Archivo **{meta['file_name']}** cargado correctamente.")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Filas", f"{df.shape[0]:,}")
            c2.metric("Columnas", f"{df.shape[1]:,}")
            c3.metric("Formato", meta["formato"])
            c4.metric("Memoria", human_readable_bytes(df.memory_usage(deep=True).sum()))

            with st.expander("Detalles técnicos de lectura"):
                st.write(f"- Codificación detectada: `{meta['encoding']}`")
                st.write(f"- Separador detectado: `{meta['separador']}`")

            st.markdown("**Vista previa (primeras 20 filas):**")
            st.dataframe(df.head(20), use_container_width=True)

        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")
    elif st.session_state.get("df") is not None:
        st.info(f"Dataset activo: **{st.session_state.file_name}**")
        st.dataframe(st.session_state.df.head(20), use_container_width=True)
    else:
        st.info("Aún no se ha cargado ningún dataset.")
