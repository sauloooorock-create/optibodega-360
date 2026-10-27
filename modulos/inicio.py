"""Página de inicio: resumen ejecutivo, estado de los módulos y arranque rápido."""

from datetime import date, timedelta

import streamlit as st

from modulos import database as db
from modulos import ui
from modulos.mermas import generar_datos_demo


def _datos_30_dias() -> tuple[float, int, str, float]:
    """Pérdida total, eventos, producto crítico y su pérdida en los últimos 30 días."""
    ini = (date.today() - timedelta(days=29)).isoformat()
    df = db.query_df(
        "SELECT producto, costo_total FROM mermas WHERE fecha >= ?", (ini,)
    )
    if df.empty:
        return 0.0, 0, "—", 0.0
    top = df.groupby("producto")["costo_total"].sum().sort_values(ascending=False)
    return float(df["costo_total"].sum()), len(df), top.index[0], float(top.iloc[0])


def _acciones_abiertas() -> int:
    filas = db.query_df(
        "SELECT COUNT(*) AS n FROM acciones_mermas WHERE estado IN ('Pendiente', 'En proceso')"
    )
    return int(filas["n"].iloc[0])


def _banner_demo() -> None:
    """Portada vacía: un botón para llenar la app con un escenario de demostración."""
    with st.container(border=True):
        st.markdown("#### 🚀 Empieza con un escenario de demostración")
        st.write(
            "Aún no hay registros de merma. Carga 90 días de datos simulados de una tienda "
            "con patrón 80/20 y explora el Pareto, el control estadístico y el plan de acción "
            "en menos de un minuto."
        )
        if st.button("🎲 Cargar escenario de demostración", type="primary",
                     use_container_width=True):
            n = generar_datos_demo()
            st.session_state["inicio_flash"] = f"Listo: se cargaron {n} registros de merma."
            st.rerun()


def _metricas(total: float, eventos: int, producto: str, costo_producto: float,
                acciones: int) -> None:
    c = st.columns(4)
    c[0].metric("Merma últimos 30 días", ui.money(total) if eventos else "—")
    c[1].metric("Eventos registrados (30 días)", f"{eventos:,}")
    c[2].metric("Producto crítico", producto,
                ui.money(costo_producto) if eventos else None, delta_color="off")
    c[3].metric("Acciones de mejora abiertas", acciones)


def _tarjeta(titulo: str, herramienta: str, linea_viva: str, listo: bool,
             pagina=None, etiqueta_boton: str = "") -> None:
    with st.container(border=True):
        if listo:
            st.markdown(":green-badge[Operativo]")
        else:
            st.markdown(":orange-badge[Próximamente]")
        st.markdown(f"##### {titulo}")
        st.caption(herramienta)
        st.write(linea_viva)
        if listo and pagina is not None:
            st.page_link(pagina, label=etiqueta_boton, icon="➡️")


def render(pagina_mermas=None) -> None:
    sucursal = st.session_state.get("sucursal", "")
    ui.page_header(
        "OptiBodega 360",
        f"Mejora continua y optimización operativa en tiempo real · {sucursal}",
        "🏪",
    )

    if "inicio_flash" in st.session_state:
        st.success(st.session_state.pop("inicio_flash"))

    total, eventos, producto, costo_producto = _datos_30_dias()
    acciones = _acciones_abiertas()

    if eventos == 0 and acciones == 0:
        _banner_demo()

    st.markdown("##### 📊 Resumen de los últimos 30 días")
    _metricas(total, eventos, producto, costo_producto, acciones)

    st.markdown("##### 🧩 Módulos")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _tarjeta("Cuellos de botella", "Teoría de Restricciones",
                 "Colas en cajas, flujo del estacionamiento y descarga en recibo.",
                 listo=False)
    with c2:
        linea = (f"**{ui.money(total)}** perdidos en 30 días. Producto crítico: "
                 f"**{producto}**." if eventos else
                 "Registra mermas y descubre los pocos vitales con el Pareto 80/20.")
        _tarjeta("Mermas y costos", "Diagrama de Pareto 80/20", linea, listo=True,
                 pagina=pagina_mermas, etiqueta_boton="Abrir Mermas y Costos")
    with c3:
        _tarjeta("Layout y recorridos", "Diagrama de recorrido · rutas óptimas",
                 "Distancias almacén → pasillos y ruta de surtido mínima.", listo=False)
    with c4:
        _tarjeta("Cuadro de mando Kaizen", "KPIs por turno",
                 "Eficiencia, tiempos muertos y cumplimiento de metas.", listo=False)

    st.markdown("##### 🔄 Ciclo PHVA (Deming)")
    p, h, v, a = st.columns(4)
    p.markdown("**1 · Planear**  \nIdentifica la restricción o los pocos vitales con datos.")
    h.markdown("**2 · Hacer**  \nImplementa acciones en el piso: 5S, FEFO, rutas.")
    v.markdown("**3 · Verificar**  \nMide con KPIs y gráficas de control si funcionó.")
    a.markdown("**4 · Actuar**  \nEstandariza lo que sirve y repite el ciclo.")

    with st.expander("🚀 Cómo usar el sistema"):
        st.markdown(
            "1. Abre **Mermas y Costos** desde el menú o la tarjeta de arriba.\n"
            "2. Carga la demostración o captura tus primeras mermas.\n"
            "3. Revisa el **Pareto** para identificar los productos y departamentos clase A.\n"
            "4. Registra acciones correctivas en el **Plan de acción** y dales seguimiento.\n"
            "5. Descarga el reporte en Excel para los anexos de la tesis."
        )
    st.caption(f"Base de datos: {db.DB_PATH.name} · {db.contar('mermas'):,} registros de merma")
