"""Sistema visual compartido: colores, tarjetas, encabezados y gráficas."""

from __future__ import annotations

import plotly.io as pio
import streamlit as st

from modulos import __app_name__, __version__

# Paleta para la clasificación ABC y los semáforos
COLOR_A = "#D32F2F"        # pocos vitales · rojo
COLOR_B = "#F57C00"        # zona intermedia · ámbar
COLOR_C = "#90A4AE"        # muchos triviales · gris
COLOR_LINEA = "#1565C0"    # líneas y acento frío
COLOR_PRIMARIO = "#2E7D32" # marca · verde

# Gráficas con un solo estilo en todo el sistema
pio.templates.default = "plotly_white"

_CSS = """
<style>
/* ---------- Base ---------- */
.block-container {padding-top: 1.4rem; padding-bottom: 4rem; max-width: 1280px;}
h1, h2, h3, h4 {letter-spacing: -0.01em;}
button[data-baseweb="tab"] {font-weight: 600; font-size: 0.95rem;}
div[data-baseweb="tab-highlight"] {background: #2E7D32 !important;}

/* ---------- Encabezado tipo hero ---------- */
.ob-hero {
    background: linear-gradient(120deg, #1B5E20 0%, #2E7D32 50%, #43A047 100%);
    color: #fff; border-radius: 18px; padding: 22px 26px; margin: 0 0 18px 0;
    box-shadow: 0 8px 26px rgba(27, 94, 32, .22);
    display: flex; align-items: center; gap: 16px;
    animation: ob-entra .5s ease both;
}
.ob-hero .ob-icono {font-size: 2.3rem; line-height: 1;}
.ob-hero h1 {color: #fff; font-size: 1.6rem; font-weight: 800; margin: 0; padding: 0;}
.ob-hero p {color: rgba(255,255,255,.9); margin: 4px 0 0 0; font-size: .95rem;}

/* ---------- Indicadores como tarjetas ---------- */
div[data-testid="stMetric"] {
    background: rgba(46, 125, 50, .05);
    border: 1px solid rgba(46, 125, 50, .18);
    border-top: 4px solid #2E7D32;
    border-radius: 14px;
    padding: 14px 16px 12px 16px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, .05);
    transition: transform .18s ease, box-shadow .18s ease;
    animation: ob-entra .45s ease both;
}
div[data-testid="stMetric"]:hover {transform: translateY(-3px); box-shadow: 0 10px 24px rgba(0,0,0,.10);}
div[data-testid="stMetric"] label p {
    font-size: .74rem; text-transform: uppercase; letter-spacing: .05em; opacity: .72; font-weight: 600;
}
div[data-testid="stMetricValue"] {font-size: 1.85rem !important; font-weight: 800;}

/* ---------- Tarjetas de módulo ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"] {
    transition: transform .18s ease, box-shadow .18s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {box-shadow: 0 10px 26px rgba(0,0,0,.09);}

/* ---------- Insights (lectura automática) ---------- */
.ob-insight {
    border-left: 5px solid #1565C0; background: rgba(21, 101, 192, .06);
    border-radius: 10px; padding: 12px 16px; margin: 6px 0 16px 0; font-size: .95rem;
    animation: ob-entra .4s ease both;
}
.ob-insight b {font-weight: 700;}

/* ---------- Sección ---------- */
.ob-seccion {font-size: 1.05rem; font-weight: 700; margin: 18px 0 6px 0; opacity: .9;}

/* ---------- Animación de entrada ---------- */
@keyframes ob-entra {
    from {opacity: 0; transform: translateY(8px);}
    to   {opacity: 1; transform: translateY(0);}
}

/* ---------- Móvil ---------- */
@media (max-width: 640px) {
    .block-container {padding-left: 16px; padding-right: 16px;}
    .ob-hero {padding: 18px 18px; border-radius: 14px;}
    .ob-hero h1 {font-size: 1.3rem;}
    div[data-testid="stMetricValue"] {font-size: 1.5rem !important;}
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(titulo: str, subtitulo: str = "", icono: str = "") -> None:
    st.markdown(
        f"""<div class="ob-hero"><div class="ob-icono">{icono}</div>
        <div><h1>{titulo}</h1><p>{subtitulo}</p></div></div>""",
        unsafe_allow_html=True,
    )


def seccion(texto: str) -> None:
    st.markdown(f'<div class="ob-seccion">{texto}</div>', unsafe_allow_html=True)


def insight(texto_html: str) -> None:
    st.markdown(f'<div class="ob-insight">{texto_html}</div>', unsafe_allow_html=True)


def tarjeta_modulo(titulo: str, herramienta: str, descripcion: str, listo: bool) -> None:
    badge = ('<span style="background:rgba(46,125,50,.15);color:#2E7D32;font-weight:600;'
             'font-size:.72rem;padding:2px 9px;border-radius:999px;">Operativo</span>'
             if listo else
             '<span style="background:rgba(245,124,0,.15);color:#B26A00;font-weight:600;'
             'font-size:.72rem;padding:2px 9px;border-radius:999px;">Próximamente</span>')
    st.markdown(
        f"""<div style="border:1px solid rgba(128,128,128,.25);border-radius:14px;padding:16px;">
        {badge}<h4 style="margin:8px 0 2px 0;">{titulo}</h4>
        <div style="font-size:.82rem;opacity:.75;">{herramienta}</div>
        <div style="font-size:.92rem;margin-top:6px;">{descripcion}</div></div>""",
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
        if "sucursal" not in st.session_state:
            st.session_state["sucursal"] = "Sucursal 001"
        st.text_input("Sucursal", key="sucursal",
                      help="Aparece en reportes y exportaciones.")
        st.caption(f"Versión {__version__} · Tesis de Ingeniería Industrial")
