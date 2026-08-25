"""
app.py
Punto de entrada de la aplicación Streamlit.
Ensambla los 5 módulos: Ingesta, EDA, Wrangling, Machine Learning y Copiloto de IA.
"""
import streamlit as st

from config import APP_TITLE, APP_ICON
from utils.session_state import init_session_state
from modules import data_ingestion, eda, data_wrangling, machine_learning
from modules.ai_copilot import ui_chat as ai_copilot

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
init_session_state()

# --- Estilos ligeros ---
st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title(APP_TITLE)
st.caption("Análisis, limpieza, transformación y Machine Learning sobre tus datos, con un copiloto de IA integrado.")

with st.sidebar:
    st.header("Navegación")
    page = st.radio(
        "Módulo",
        [
            "📥 1. Ingesta de Datos",
            "🔬 2. Análisis Exploratorio (EDA)",
            "🧰 3. Limpieza y Transformación",
            "🤖 4. Machine Learning",
            "💬 5. Copiloto de IA",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    if st.session_state.get("df") is not None:
        st.success(f"Dataset activo:\n**{st.session_state.file_name}**")
        st.write(f"{st.session_state.df.shape[0]:,} filas × {st.session_state.df.shape[1]:,} columnas")
    else:
        st.info("Sin dataset cargado todavía.")

PAGES = {
    "📥 1. Ingesta de Datos": data_ingestion.render,
    "🔬 2. Análisis Exploratorio (EDA)": eda.render,
    "🧰 3. Limpieza y Transformación": data_wrangling.render,
    "🤖 4. Machine Learning": machine_learning.render,
    "💬 5. Copiloto de IA": ai_copilot.render,
}

PAGES[page]()
