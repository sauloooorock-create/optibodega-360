"""
OptiBodega 360 · Sistema de mejora continua para tiendas de autoservicio
Tesis de Ingeniería Industrial y de Sistemas

Ejecutar localmente:
    pip install -r requirements.txt
    streamlit run app.py
"""

import streamlit as st

from modulos import database as db
from modulos import inicio, mermas, proximamente, ui

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


# ---------------------------------------------------------------------
# Páginas (cada una delega en su módulo)
# ---------------------------------------------------------------------
def pagina_cuellos_botella():
    proximamente.render("toc")


def pagina_mermas():
    mermas.render()


def pagina_layout():
    proximamente.render("layout")


def pagina_kaizen():
    proximamente.render("kaizen")


p_mermas = st.Page(pagina_mermas, title="Mermas y Costos (Pareto)", icon="📉",
                   url_path="mermas")


def pagina_inicio():
    inicio.render(pagina_mermas=p_mermas)


navegacion = st.navigation(
    {
        "General": [
            st.Page(pagina_inicio, title="Inicio", icon="🏠", default=True),
        ],
        "Módulos de Ingeniería Industrial": [
            st.Page(pagina_cuellos_botella, title="Cuellos de Botella (TOC)", icon="🚦",
                    url_path="cuellos-de-botella"),
            p_mermas,
            st.Page(pagina_layout, title="Layout y Recorridos", icon="🗺️",
                    url_path="layout"),
            st.Page(pagina_kaizen, title="Cuadro de Mando Kaizen", icon="🎯",
                    url_path="kaizen"),
        ],
    }
)
navegacion.run()
