"""Página de inicio: presentación del sistema y resumen ejecutivo."""

from datetime import date, timedelta

import streamlit as st

from modulos import database as db
from modulos import ui


def _resumen_mermas() -> None:
    hoy = date.today()
    ini = (hoy - timedelta(days=29)).isoformat()
    df = db.query_df(
        "SELECT departamento, producto, costo_total FROM mermas WHERE fecha >= ?", (ini,)
    )
    acciones = db.query_df(
        "SELECT estado FROM acciones_mermas WHERE estado IN ('Pendiente', 'En proceso')"
    )
    c = st.columns(4)
    if df.empty:
        c[0].metric("Merma últimos 30 días", "—")
        c[1].metric("Eventos registrados", "0")
        c[2].metric("Producto crítico", "—")
    else:
        prod = df.groupby("producto")["costo_total"].sum().sort_values(ascending=False)
        c[0].metric("Merma últimos 30 días", ui.money(df["costo_total"].sum()))
        c[1].metric("Eventos registrados", f"{len(df):,}")
        c[2].metric("Producto crítico", prod.index[0], ui.money(prod.iloc[0]), delta_color="off")
    c[3].metric("Acciones de mejora abiertas", len(acciones))


def render(pagina_mermas=None) -> None:
    sucursal = st.session_state.get("sucursal", "")
    ui.page_header(
        "OptiBodega 360",
        f"Sistema de mejora continua y optimización operativa en tiempo real · {sucursal}",
        "🏪",
    )

    st.markdown(
        "Plataforma de apoyo a la toma de decisiones para una **tienda de autoservicio** que "
        "integra herramientas clásicas de **Ingeniería Industrial y de Sistemas**: Teoría de "
        "Restricciones, análisis de Pareto, estudio de recorridos y gestión visual Kaizen. "
        "Cada módulo convierte los datos operativos del piso de venta en indicadores y "
        "acciones concretas."
    )

    st.markdown("##### 📊 Resumen ejecutivo")
    _resumen_mermas()

    st.markdown("##### 🧩 Módulos del sistema")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.tarjeta_modulo("Cuellos de botella y logística", "Teoría de Restricciones",
                          "Colas en cajas, flujo del estacionamiento y descarga en recibo.",
                          listo=False)
    with c2:
        ui.tarjeta_modulo("Mermas y costos", "Diagrama de Pareto 80/20",
                          "Registro, clasificación ABC, control estadístico y plan de acción.",
                          listo=True)
        if pagina_mermas is not None:
            st.page_link(pagina_mermas, label="Abrir módulo →", icon="📉")
    with c3:
        ui.tarjeta_modulo("Layout y recorridos", "Diagrama de recorrido · rutas óptimas",
                          "Distancias almacén → pasillos y ruta de surtido mínima.",
                          listo=False)
    with c4:
        ui.tarjeta_modulo("Cuadro de mando Kaizen", "KPIs por turno",
                          "Eficiencia, tiempos muertos y cumplimiento de metas.",
                          listo=False)

    st.markdown("##### 🔄 Metodología: ciclo PHVA (Deming)")
    p, h, v, a = st.columns(4)
    p.markdown("**Planear**  \nIdentificar la restricción o los pocos vitales con datos "
               "(Pareto, TOC).")
    h.markdown("**Hacer**  \nImplementar acciones correctivas en el piso de venta "
               "(5S, FEFO, rutas).")
    v.markdown("**Verificar**  \nMedir con KPIs y gráficas de control si el cambio funcionó.")
    a.markdown("**Actuar**  \nEstandarizar lo que funciona y repetir el ciclo (Kaizen).")

    with st.expander("🚀 Cómo empezar"):
        st.markdown(
            "1. Abre **Mermas y Costos** en el menú lateral.\n"
            "2. Genera datos de demostración o captura tus primeras mermas.\n"
            "3. Revisa el **Pareto** para identificar los productos y departamentos clase A.\n"
            "4. Registra acciones correctivas en el **Plan de acción** y dales seguimiento.\n"
            "5. Exporta el reporte en Excel para los anexos de la tesis."
        )
    st.caption(f"Base de datos: {db.DB_PATH.name} · {db.contar('mermas'):,} registros de merma")
