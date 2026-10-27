"""Portada: lo esencial de un vistazo."""

from datetime import date, timedelta

import streamlit as st

from modulos import database as db
from modulos import mermas, ui


def _datos_30_dias() -> tuple[float, int, str, float]:
    ini = (date.today() - timedelta(days=29)).isoformat()
    df = db.query_df("SELECT producto, costo_total FROM mermas WHERE fecha >= ?", (ini,))
    if df.empty:
        return 0.0, 0, "—", 0.0
    top = df.groupby("producto")["costo_total"].sum().sort_values(ascending=False)
    return float(df["costo_total"].sum()), len(df), top.index[0], float(top.iloc[0])


def _acciones_abiertas() -> int:
    filas = db.query_df(
        "SELECT COUNT(*) AS n FROM acciones_mermas WHERE estado IN ('Pendiente', 'En proceso')"
    )
    return int(filas["n"].iloc[0])


def _tarjeta(icono: str, titulo: str, linea: str, pagina) -> None:
    with st.container(border=True):
        st.markdown(f"##### {icono} {titulo}")
        st.write(linea)
        if pagina is not None:
            st.page_link(pagina, label="Abrir →")


def render(pagina_mermas=None, pagina_toc=None, pagina_kaizen=None, pagina_layout=None) -> None:
    sucursal = st.session_state.get("sucursal", "")
    ui.page_header("OptiBodega 360", f"Mejora continua en tiempo real · {sucursal}", "🏪")

    total, eventos, producto, costo_producto = _datos_30_dias()
    acciones = _acciones_abiertas()

    c = st.columns(4)
    c[0].metric("Merma · 30 días", ui.money(total) if eventos else "—")
    c[1].metric("Eventos", f"{eventos:,}")
    c[2].metric("Producto crítico", producto, ui.money(costo_producto) if eventos else None,
                delta_color="off")
    c[3].metric("Acciones abiertas", acciones)

    if eventos == 0:
        st.info("👈 Aún no hay datos. Pulsa **Cargar demostración** en el menú lateral para "
                "explorar los cuatro módulos.")

    df = mermas.obtener_mermas()
    if not df.empty:
        ui.seccion("Dónde se pierde el dinero · últimos 90 días")
        par = mermas.calcular_pareto(df, "producto")
        fig = mermas.grafica_pareto(par, "producto", "costo", top_n=10, umbral=80)
        fig.update_layout(height=400)
        st.plotly_chart(fig, key="inicio_pareto")
        ui.insight(mermas._texto_insight(par, "Producto", "costo"))

    ui.seccion("Módulos")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _tarjeta("🚦", "Cuellos de botella", "Colas, estacionamiento y recibo.", pagina_toc)
    with c2:
        _tarjeta("📉", "Mermas y costos", "Pareto 80/20 y plan de acción.", pagina_mermas)
    with c3:
        _tarjeta("🗺️", "Layout y recorridos", "Ruta de surtido y reubicación.", pagina_layout)
    with c4:
        _tarjeta("🎯", "Cuadro Kaizen", "Semáforo por turno y mejoras.", pagina_kaizen)
