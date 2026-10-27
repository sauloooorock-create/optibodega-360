"""
OptiBodega 360 · Sistema de mejora continua para tiendas de autoservicio
Tesis de Ingeniería Industrial y de Sistemas

Ejecutar localmente:
    pip install -r requirements.txt
    streamlit run app.py
"""

import streamlit as st

from modulos import database as db
from modulos import inicio, kaizen, layout, mermas, respaldo, sensibilidad, toc, ui

st.set_page_config(
    page_title="OptiBodega 360 · Mejora Continua",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def _arranque() -> bool:
    """Crea la base de datos y el catálogo una sola vez por proceso del servidor."""
    db.init_db()
    return True


_arranque()
ui.inject_css()
ui.sidebar_info()


def _sidebar_demo() -> None:
    """Un solo botón llena los cuatro módulos; disponible en cualquier página."""
    with st.sidebar:
        st.divider()
        st.markdown("**Datos de prueba**")
        st.caption("Carga 30–90 días simulados de los cuatro módulos.")
        if st.button("🎲 Cargar demostración", use_container_width=True):
            with st.spinner("Generando datos…"):
                n_m = mermas.generar_datos_demo()
                n_t = toc.generar_demo_toc()
                n_k = kaizen.generar_demo_kaizen()
                n_l = layout.generar_demo_layout(layout.PARAM_DEFAULT)
            st.session_state["flash_global"] = (
                f"Demostración lista: {n_m} mermas · {n_t} tiempos · {n_k} turnos · {n_l} ubicaciones.")
            st.rerun()
        if st.session_state.pop("flash_global", None):
            st.success("Demostración lista.")


_sidebar_demo()


# ---------------------------------------------------------------------
# Páginas (cada una delega en su módulo)
# ---------------------------------------------------------------------
def pagina_cuellos_botella():
    toc.render()


def pagina_mermas():
    mermas.render()


def pagina_layout():
    layout.render()


def pagina_kaizen():
    kaizen.render()


def pagina_sensibilidad():
    sensibilidad.render()


p_mermas = st.Page(pagina_mermas, title="Mermas y Costos (Pareto)", icon="📉",
                   url_path="mermas")


p_toc = st.Page(pagina_cuellos_botella, title="Cuellos de Botella (TOC)", icon="🚦",
                url_path="cuellos-de-botella")


p_kaizen = st.Page(pagina_kaizen, title="Cuadro de Mando Kaizen", icon="🎯",
                   url_path="kaizen")
p_layout = st.Page(pagina_layout, title="Layout y Recorridos", icon="🗺️", url_path="layout")
p_sensibilidad = st.Page(pagina_sensibilidad, title="Análisis de sensibilidad", icon="🧪",
                         url_path="sensibilidad")


def pagina_respaldo():
    respaldo.render()


p_respaldo = st.Page(pagina_respaldo, title="Respaldo y reporte", icon="💾",
                     url_path="respaldo")


def pagina_inicio():
    inicio.render(pagina_mermas=p_mermas, pagina_toc=p_toc, pagina_kaizen=p_kaizen,
                  pagina_layout=p_layout)


navegacion = st.navigation(
    {
        "General": [
            st.Page(pagina_inicio, title="Inicio", icon="🏠", default=True),
            p_respaldo,
        ],
        "Módulos de Ingeniería Industrial": [
            p_toc,
            p_mermas,
            p_layout,
            p_kaizen,
            p_sensibilidad,
        ],
    }
)
navegacion.run()
