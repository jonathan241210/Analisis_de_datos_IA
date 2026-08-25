"""
utils/session_state.py
Inicialización y helpers para el estado global de la sesión de Streamlit.
Mantener el df actual, su historial (para poder deshacer) y el historial del chat.
"""
import streamlit as st
import pandas as pd


def init_session_state():
    defaults = {
        "df": None,                 # DataFrame activo
        "df_original": None,        # copia intacta tal como se cargó
        "file_name": None,
        "history": [],              # pila de DataFrames anteriores (undo)
        "chat_history": [],         # lista de mensajes {role, content}
        "selected_model_key": "nvidia",
        "last_generated_code": None,
        "pending_figures": [],      # figuras generadas por el último código ejecutado
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_dataframe(df: pd.DataFrame, file_name: str | None = None, reset_history: bool = True):
    st.session_state.df = df
    st.session_state.df_original = df.copy()
    if file_name:
        st.session_state.file_name = file_name
    if reset_history:
        st.session_state.history = []


def push_history_snapshot():
    """Guarda una copia del df actual antes de aplicar una transformación (para poder deshacer)."""
    if st.session_state.df is not None:
        st.session_state.history.append(st.session_state.df.copy())
        # limitar la pila para no consumir memoria indefinidamente
        st.session_state.history = st.session_state.history[-15:]


def undo_last_transformation() -> bool:
    if st.session_state.history:
        st.session_state.df = st.session_state.history.pop()
        return True
    return False


def update_dataframe(new_df: pd.DataFrame):
    push_history_snapshot()
    st.session_state.df = new_df


def has_data() -> bool:
    return st.session_state.get("df") is not None
