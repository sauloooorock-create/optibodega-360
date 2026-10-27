"""
OptiBodega 360 · Sistema de mejora continua para tiendas de autoservicio
Tesis de Ingeniería Industrial y de Sistemas

Ejecutar localmente:
    pip install -r requirements.txt
    streamlit run app.py
"""

import streamlit as st

from modulos import database as db
from modulos import inicio, kaizen, mermas, proximamente, toc, ui

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
    toc.render()


def pagina_mermas():
    mermas.render()


def pagina_layout():
    proximamente.render("layout")


def pagina_kaizen():
    kaizen.render()


p_mermas = st.Page(pagina_mermas, title="Mermas y Costos (Pareto)", icon="📉",
                   url_path="mermas")


p_toc = st.Page(pagina_cuellos_botella, title="Cuellos de Botella (TOC)", icon="🚦",
                url_path="cuellos-de-botella")


p_kaizen = st.Page(pagina_kaizen, title="Cuadro de Mando Kaizen", icon="🎯",
                   url_path="kaizen")


def pagina_inicio():
    inicio.render(pagina_mermas=p_mermas, pagina_toc=p_toc, pagina_kaizen=p_kaizen)


navegacion = st.navigation(
    {
        "General": [
            st.Page(pagina_inicio, title="Inicio", icon="🏠", default=True),
        ],
        "Módulos de Ingeniería Industrial": [
            p_toc,
            p_mermas,
            st.Page(pagina_layout, title="Layout y Recorridos", icon="🗺️",
                    url_path="layout"),
            p_kaizen,
        ],
    }
)
navegacion.run()
