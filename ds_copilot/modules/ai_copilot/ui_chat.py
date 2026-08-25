"""
modules/ai_copilot/ui_chat.py
Renderiza el chat del Copiloto de IA: selector de modelo, burbujas de conversación
"""
import streamlit as st
import plotly.graph_objects as go

from config import AI_MODELS, DEFAULT_MODEL_KEY
from modules.ai_copilot.client import call_ai_model, AIClientError
from modules.ai_copilot.context_builder import build_context
from modules.ai_copilot.prompts import build_user_message
from modules.ai_copilot.executor import extract_python_code, run_generated_code
from utils.session_state import update_dataframe


def _model_selector():
    st.markdown("**Motor de IA**")
    keys = list(AI_MODELS.keys())
    labels = [AI_MODELS[k].label for k in keys]
    current_index = keys.index(st.session_state.get("selected_model_key", DEFAULT_MODEL_KEY))
    chosen_label = st.radio(
        "Selecciona el modelo", labels, index=current_index,
        horizontal=True, label_visibility="collapsed", key="ai_model_radio",
    )
    chosen_key = keys[labels.index(chosen_label)]
    st.session_state.selected_model_key = chosen_key
    st.caption(AI_MODELS[chosen_key].description)


def _render_code_block(code: str, block_id: str):
    """Bloque de código con botones Copiar (vía JS) y Ejecutar (vía Streamlit)."""
    st.code(code, language="python")
    # Eliminado el botón de copiar por diseño solicitado. Solo ejecutar.
    if st.button("▶️ Ejecutar Código", key=f"exec_{block_id}"):
        _execute_code_block(code, block_id)


def _execute_code_block(code: str, block_id: str):
    df = st.session_state.get("df")
    if df is None:
        st.error("No hay un dataset cargado para ejecutar el código.")
        return

    with st.spinner("Ejecutando código sobre el DataFrame..."):
        # Permitimos que el código generado use `st` ya que proviene de la UI
        try:
            result = run_generated_code(code, df, allow_streamlit=True)
        except Exception as e:
            # Atrapamos excepciones inesperadas para evitar UnboundLocalError
            result = type("R", (), {"success": False, "error": str(e), "stdout": ""})()

    if not result.success:
        st.error(f"❌ Error al ejecutar: {result.error}")
        if result.stdout:
            with st.expander("Registro de ejecución"):
                st.text(result.stdout)
        return

    st.success("✅ Código ejecutado correctamente.")
    # Mostrar stdout solo si no hay una tabla auxiliar: si el usuario pidió
    # explícitamente una tabla (display_df), no mostramos el texto impreso.
    display_df_check = getattr(result, "display_df", None)
    if result.stdout and (
        display_df_check is None or (hasattr(display_df_check, "empty") and display_df_check.empty)
    ):
        with st.expander("Registro de ejecución"):
            st.text(result.stdout)

    display_df = getattr(result, "display_df", None)

    if result.fig is not None:
        # Si el código también generó un DataFrame auxiliar para mostrar,
        # priorizamos mostrar la tabla solicitada por el usuario y NO renderizamos
        # la figura automáticamente para evitar outputs no solicitados.
        if display_df is None or (isinstance(display_df, bool) and not display_df):
            st.session_state.pending_figures.append(result.fig)
            if isinstance(result.fig, go.Figure):
                st.plotly_chart(
                    result.fig,
                    use_container_width=True,
                    key=f"plotly_chart_{block_id}",
                )
            else:
                # Figura no-Plotly (p. ej. Matplotlib) generada pese a las reglas del
                # system prompt — se renderiza igual como respaldo, sin romper la app.
                st.pyplot(result.fig)

    if display_df is not None and not display_df.empty:
        st.info("📋 Resultado (tabla auxiliar generada)")
        # Centrar la tabla para mejorar el diseño
        left, mid, right = st.columns([1, 6, 1])
        with mid:
            # Mostrar exactamente la DataFrame auxiliar (no forzar .head)
            st.dataframe(display_df, use_container_width=True)
        # No renderizar figuras si la intención del usuario fue mostrar tablas
        # explícitas (ej. head) para evitar outputs no solicitados.
        return

    # Si el código reasignó `df`, actualizamos la tabla global en sesión.
    if result.df is not None and not result.df.equals(df):
        update_dataframe(result.df)
        st.info("📊 La tabla global del dataset se actualizó con el resultado.")
        left, mid, right = st.columns([1, 6, 1])
        with mid:
            st.dataframe(result.df.head(10), use_container_width=True)


def _render_message(msg: dict, idx: int):
    with st.chat_message(msg["role"]):
        content = msg["content"]

        if msg["role"] != "assistant":
            st.markdown(content)
            return

        code_blocks = extract_python_code(content)

        if not code_blocks:
            # Sin bloque ```python```: es un mensaje de error/aviso del cliente
            # de IA (p. ej. ⚠️ falta la clave de API), no una respuesta de código.
            st.markdown(content)
            return

        # Solo se renderiza el código limpio. Cualquier texto introductorio,
        # explicación posterior o sección de "Salida esperada" que el modelo
        # haya colado fuera del bloque ```python``` se descarta intencionalmente:
        # el system prompt exige código puro, y esto es el respaldo en la UI.
        for i, block in enumerate(code_blocks):
            _render_code_block(block, block_id=f"{idx}_{i}")


def render():
    st.subheader("💬 Copiloto de IA Conversacional")
    df = st.session_state.get("df")
    if df is None:
        st.warning("Carga un dataset primero para poder chatear sobre él.")
        return

    _model_selector()
    st.divider()

    for idx, msg in enumerate(st.session_state.chat_history):
        _render_message(msg, idx)

    user_query = st.chat_input("Pregúntale algo a tu copiloto sobre el dataset...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        context_block = build_context(st.session_state.df, user_query)
        combined_message = build_user_message(user_query, context_block)

        with st.chat_message("assistant"):
            with st.spinner("El copiloto está pensando..."):
                try:
                    reply = call_ai_model(
                        st.session_state.selected_model_key,
                        st.session_state.chat_history[:-1],
                        combined_message,
                    )
                except AIClientError as e:
                    reply = f"⚠️ {e}"
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            _render_message(
                {"role": "assistant", "content": reply},
                idx=len(st.session_state.chat_history),
            )

    # Botón para descargar el dataset actual con todos los cambios realizados
    st.divider()
    st.markdown("**Descargar dataset con cambios**")
    df_current = st.session_state.get("df")
    if df_current is not None:
        try:
            csv_bytes = df_current.to_csv(index=False).encode("utf-8")
            left, mid, right = st.columns([1, 6, 1])
            with mid:
                st.download_button(
                    label="⬇️ Descargar dataset (CSV)",
                    data=csv_bytes,
                    file_name="dataset_modificado.csv",
                    mime="text/csv",
                    key="download_dataset",
                )
        except Exception:
            st.error("No se pudo preparar el dataset para descarga.")
