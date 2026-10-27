"""Componentes visuales y estilos compartidos por todas las páginas."""

from __future__ import annotations

import streamlit as st

from modulos import __app_name__, __version__

# Paleta para la clasificación ABC del Pareto
COLOR_A = "#C62828"   # pocos vitales
COLOR_B = "#EF8F00"   # zona intermedia
COLOR_C = "#8D99A6"   # muchos triviales
COLOR_LINEA = "#1565C0"
COLOR_PRIMARIO = "#2E7D32"

_CSS = """
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
div[data-testid="stMetric"] {
    background: rgba(46,125,50,0.06);
    border: 1px solid rgba(46,125,50,0.22);
    border-radius: 12px;
    padding: 12px 16px;
}
div[data-testid="stMetric"] label p {font-size: 0.82rem; opacity: .85;}
.ob-header {
    border-left: 6px solid #2E7D32;
    padding: 4px 0 4px 14px;
    margin-bottom: 1rem;
}
.ob-header h1 {font-size: 1.8rem; margin: 0; padding: 0;}
.ob-header p {margin: 2px 0 0 0; opacity: .75;}
.ob-card {
    border: 1px solid rgba(128,128,128,0.28);
    border-radius: 14px;
    padding: 16px 18px;
    height: 100%;
}
.ob-card h4 {margin: 0 0 6px 0;}
.ob-badge {
    display: inline-block; font-size: .72rem; font-weight: 600;
    padding: 2px 9px; border-radius: 999px; margin-bottom: 8px;
}
.ob-ok   {background: rgba(46,125,50,.15); color: #2E7D32;}
.ob-wip  {background: rgba(239,143,0,.15); color: #B26A00;}
.ob-insight {
    border-radius: 12px; padding: 14px 18px; margin: 8px 0 14px 0;
    background: rgba(21,101,192,0.07); border: 1px solid rgba(21,101,192,0.25);
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(titulo: str, subtitulo: str = "", icono: str = "") -> None:
    st.markdown(
        f"""<div class="ob-header"><h1>{icono} {titulo}</h1>
        <p>{subtitulo}</p></div>""",
        unsafe_allow_html=True,
    )


def insight(texto_html: str) -> None:
    st.markdown(f'<div class="ob-insight">{texto_html}</div>', unsafe_allow_html=True)


def tarjeta_modulo(titulo: str, herramienta: str, descripcion: str, listo: bool) -> None:
    badge = '<span class="ob-badge ob-ok">Operativo</span>' if listo else \
            '<span class="ob-badge ob-wip">En desarrollo</span>'
    st.markdown(
        f"""<div class="ob-card">{badge}<h4>{titulo}</h4>
        <p style="margin:0 0 6px 0; font-size:.85rem; opacity:.8;"><b>{herramienta}</b></p>
        <p style="margin:0; font-size:.9rem;">{descripcion}</p></div>""",
        unsafe_allow_html=True,
    )


def money(valor: float, decimales: int = 0) -> str:
    try:
        return f"${valor:,.{decimales}f}"
    except (TypeError, ValueError):
        return "—"


def sidebar_info() -> None:
    with st.sidebar:
        st.markdown(f"### 🏪 {__app_name__}")
        st.caption("Mejora continua y optimización operativa en tiempo real")
        if "sucursal" not in st.session_state:
            st.session_state["sucursal"] = "Sucursal 001"
        st.text_input(
            "Sucursal",
            key="sucursal",
            help="Nombre de la tienda que aparecerá en reportes y exportaciones.",
        )
        st.divider()
        st.caption(f"Versión {__version__} · Tesis de Ingeniería Industrial y de Sistemas")
