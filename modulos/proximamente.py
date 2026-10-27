"""Fichas de los módulos en desarrollo (se reemplazan conforme se construyen)."""

import streamlit as st

from modulos import ui

MODULOS_FUTUROS = {
    "toc": {
        "titulo": "Cuellos de Botella y Logística",
        "icono": "🚦",
        "herramienta": "Teoría de Restricciones (TOC) · Teoría de colas · Simulación",
        "incluira": [
            "Registro de llegadas y tiempos de servicio en cajas (cronometraje).",
            "Modelo de colas M/M/c: utilización ρ, Lq, Wq y número óptimo de cajas abiertas.",
            "Simulación de eventos discretos por hora del día (escenarios «¿qué pasa si…?»).",
            "Flujo vehicular del estacionamiento: ocupación y tiempos de búsqueda de cajón.",
            "Recibo de proveedores: tiempo de descarga por andén y programación de citas.",
            "Los 5 pasos de TOC: identificar, explotar, subordinar, elevar y repetir.",
        ],
    },
    "layout": {
        "titulo": "Optimización de Layout y Recorridos",
        "icono": "🗺️",
        "herramienta": "Diagrama de recorrido · Distancia rectilínea · Ruta óptima (TSP)",
        "incluira": [
            "Plano de la tienda en cuadrícula: almacén central, andenes y pasillos de venta.",
            "Matriz de distancias rectilíneas (Manhattan) almacén → pasillos.",
            "Ruta de surtido óptima (vecino más cercano + mejora 2-opt) vs. ruta actual.",
            "Diagrama de operaciones y recorrido con simbología ASME.",
            "Análisis Desde-Hacia y ubicación por rotación (clase ABC de los pasillos).",
        ],
    },
    "kaizen": {
        "titulo": "Cuadro de Mando Kaizen",
        "icono": "🎯",
        "herramienta": "KPIs por turno · OEE adaptado · Tiempos muertos · Andon",
        "incluira": [
            "Captura por turno: metas, producción real y paros (tiempos muertos).",
            "Eficiencia operativa, productividad por colaborador y cumplimiento de metas.",
            "Semáforo tipo Andon y tendencias de mejora semana contra semana.",
            "Integración con los KPIs de mermas, colas y recorridos de los otros módulos.",
            "Registro de eventos Kaizen y lecciones aprendidas.",
        ],
    },
}


def render(clave: str) -> None:
    info = MODULOS_FUTUROS[clave]
    ui.page_header(info["titulo"], info["herramienta"], info["icono"])
    st.info("🚧 Este módulo se construirá en la siguiente etapa del proyecto. "
            "Su estructura ya está reservada en la navegación y en la base de datos.")
    st.markdown("**Lo que incluirá:**")
    for punto in info["incluira"]:
        st.markdown(f"- {punto}")
