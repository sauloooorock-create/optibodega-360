"""
Análisis de sensibilidad · ¿qué tan robustos son los resultados si los supuestos cambian?

Los valores de referencia no son mediciones de una tienda real. Este módulo muestra cómo
cambian los resultados dentro de un rango razonable para cada supuesto. Si una conclusión
se mantiene en todo el rango, es robusta; si cambia mucho, conviene medir ese parámetro.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modulos import layout, toc, ui

# Valores de referencia (supuestos documentados, no medidos)
REF = {
    "pico": 110.0, "t_caja": 2.5, "meta": 3.0, "cajas": 4,
    "cajones": 60, "autos": 70.0, "estancia": 35.0,
    "camiones": 4.0, "descarga": 45.0, "meta_r": 30.0,
}
TOPE_ESPERA = 60.0  # minutos; valores mayores se muestran como tope

SUPUESTOS = pd.DataFrame([
    ("Clientes por hora en pico", "110", "80 – 140",
     "Afluencia de una tienda de autoservicio de tamaño medio en hora pico."),
    ("Tiempo de servicio por cliente en caja", "2.5 min", "2 – 3.5 min",
     "Cobro de una canasta promedio; se puede medir con cronómetro."),
    ("Meta de espera en caja", "3 min", "2 – 5 min",
     "Criterio de servicio habitual en autoservicio."),
    ("Cajas abiertas en pico", "4", "3 – 6", "Dotación típica en hora pico."),
    ("Autos por hora (estacionamiento)", "70", "50 – 100", "Afluencia en hora pico."),
    ("Cajones de estacionamiento", "60", "40 – 80", "Tamaño de estacionamiento mediano."),
    ("Estancia promedio en la tienda", "35 min", "25 – 50 min", "Tiempo de compra promedio."),
    ("Camiones por hora (recibo)", "4", "2 – 8", "Frecuencia de entregas de proveedores."),
    ("Minutos de descarga por camión", "45", "30 – 60", "Descarga manual o con montacargas."),
    ("Velocidad de caminata del surtidor", "1.2 m/s", "0.9 – 1.4 m/s",
     "Caminata con carga ligera."),
    ("Pasillos de venta × largo", "8 × 20 m", "6–12 × 15–25 m",
     "Piso de venta de formato mediano."),
], columns=["Supuesto", "Referencia", "Rango", "Justificación"])


# =====================================================================
# Barridos
# =====================================================================
def barrido_cajas(demandas: list[float], tiempos: list[float], meta: float) -> pd.DataFrame:
    """Cajas mínimas para cumplir la meta; filas = minutos por cliente, columnas = demanda."""
    m = [[np.nan] * len(demandas) for _ in tiempos]
    for i, t in enumerate(tiempos):
        for j, d in enumerate(demandas):
            c = toc.c_minimo(d, 60 / t, meta)
            m[i][j] = np.nan if c is None else float(c)
    return pd.DataFrame(m, index=[f"{t:g} min" for t in tiempos],
                        columns=[f"{d:.0f}/h" for d in demandas])


def barrido_estacionamiento(autos: list[float], cajones: list[int], estancia: float) -> pd.DataFrame:
    """% de autos sin cajón; filas = cajones, columnas = autos por hora."""
    m = [[toc.erlang_b(a * estancia / 60, n) * 100 for a in autos] for n in cajones]
    return pd.DataFrame(m, index=[f"{n}" for n in cajones],
                        columns=[f"{a:.0f}/h" for a in autos])


def barrido_andenes(camiones: list[float], descargas: list[float], meta: float) -> pd.DataFrame:
    """Andenes mínimos para la meta de espera; filas = minutos de descarga."""
    m = [[np.nan] * len(camiones) for _ in descargas]
    for i, t in enumerate(descargas):
        for j, cam in enumerate(camiones):
            c = toc.c_minimo(cam, 60 / t, meta)
            m[i][j] = np.nan if c is None else float(c)
    return pd.DataFrame(m, index=[f"{t:.0f} min" for t in descargas],
                        columns=[f"{c:g}/h" for c in camiones])


def barrido_layout(pasillos: list[int], largos: list[float], base: dict) -> pd.DataFrame:
    """% de metros que se ahorran al reubicar por rotación, con los datos actuales."""
    m = []
    for p in pasillos:
        fila = []
        for lg in largos:
            P = dict(base, pasillos=p, largo=lg)
            df = layout.cargar(P)
            prop = layout.propuesta_por_rotacion(df, P) if not df.empty else None
            if prop is None or df.empty:
                fila.append(np.nan)
            else:
                actual = df["metros_dia"].sum()
                fila.append((actual - prop["metros_dia"].sum()) / actual * 100)
        m.append(fila)
    return pd.DataFrame(m, index=[f"{p} pasillos" for p in pasillos],
                        columns=[f"{lg:g} m" for lg in largos])


# =====================================================================
# Tornado: qué parámetro mueve más el resultado
# =====================================================================
def tornado_cajas() -> pd.DataFrame:
    def espera(pico, t_caja, cajas):
        r = toc.mmc(pico, 60 / t_caja, int(cajas))
        return min(r["Wq"], TOPE_ESPERA) if r["stable"] else TOPE_ESPERA

    base = espera(REF["pico"], REF["t_caja"], REF["cajas"])
    filas = [
        ("Clientes por hora (±20 %)", espera(REF["pico"] * 0.8, REF["t_caja"], REF["cajas"]),
         espera(REF["pico"] * 1.2, REF["t_caja"], REF["cajas"]), "80 %", "120 %"),
        ("Minutos por cliente (±20 %)", espera(REF["pico"], REF["t_caja"] * 0.8, REF["cajas"]),
         espera(REF["pico"], REF["t_caja"] * 1.2, REF["cajas"]), "−20 %", "+20 %"),
        ("Cajas abiertas (±1)", espera(REF["pico"], REF["t_caja"], REF["cajas"] + 1),
         espera(REF["pico"], REF["t_caja"], REF["cajas"] - 1), "+1 caja", "−1 caja"),
    ]
    df = pd.DataFrame(filas, columns=["Parámetro", "Espera_a", "Espera_b", "Variación_a",
                                      "Variación_b"])
    df["Base"] = base
    df["Rango"] = (df["Espera_b"] - df["Espera_a"]).abs()
    return df.sort_values("Rango", ascending=True).reset_index(drop=True)


def tornado_estacionamiento() -> pd.DataFrame:
    def bloqueo(autos, estancia, cajones):
        return toc.erlang_b(autos * estancia / 60, int(cajones)) * 100

    filas = [
        ("Autos por hora (±20 %)", bloqueo(REF["autos"] * 0.8, REF["estancia"], REF["cajones"]),
         bloqueo(REF["autos"] * 1.2, REF["estancia"], REF["cajones"]), "80 %", "120 %"),
        ("Estancia promedio (±20 %)", bloqueo(REF["autos"], REF["estancia"] * 0.8, REF["cajones"]),
         bloqueo(REF["autos"], REF["estancia"] * 1.2, REF["cajones"]), "−20 %", "+20 %"),
        ("Cajones (±10 %)", bloqueo(REF["autos"], REF["estancia"], REF["cajones"] * 1.1),
         bloqueo(REF["autos"], REF["estancia"], REF["cajones"] * 0.9), "+10 %", "−10 %"),
    ]
    df = pd.DataFrame(filas, columns=["Parámetro", "Bloqueo_a", "Bloqueo_b", "Variación_a",
                                      "Variación_b"])
    df["Base"] = bloqueo(REF["autos"], REF["estancia"], REF["cajones"])
    df["Rango"] = (df["Bloqueo_b"] - df["Bloqueo_a"]).abs()
    return df.sort_values("Rango", ascending=True).reset_index(drop=True)


# =====================================================================
# Interfaz
# =====================================================================
def _mapa(df: pd.DataFrame, titulo: str, escala: str, texto_fmt: str, key: str,
          invertir: bool = False) -> None:
    fig = px.imshow(df, text_auto=texto_fmt, aspect="auto", color_continuous_scale=escala,
                    title=titulo)
    if invertir:
        fig.update_coloraxes(reversescale=True)
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10),
                      xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, key=key)


def _tornado(df: pd.DataFrame, base: float, titulo: str, unidad: str, key: str) -> None:
    lo = df["Espera_a"] if "Espera_a" in df else df["Bloqueo_a"]
    hi = df["Espera_b"] if "Espera_b" in df else df["Bloqueo_b"]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df["Parámetro"], x=np.minimum(lo, hi) - base, orientation="h",
                         name="Baja el resultado", marker_color=ui.COLOR_PRIMARIO,
                         hovertemplate="%{y}: %{x:+.1f} " + unidad + "<extra></extra>"))
    fig.add_trace(go.Bar(y=df["Parámetro"], x=np.maximum(lo, hi) - base, orientation="h",
                         name="Sube el resultado", marker_color=ui.COLOR_A,
                         hovertemplate="%{y}: %{x:+.1f} " + unidad + "<extra></extra>"))
    fig.update_layout(barmode="overlay", title=titulo, height=300,
                      margin=dict(l=10, r=10, t=50, b=10),
                      xaxis_title=f"Cambio respecto a la referencia ({unidad})",
                      legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, key=key)


def _rango_texto(df: pd.DataFrame, unidad: str) -> str:
    vals = df.to_numpy().ravel()
    vals = vals[~np.isnan(vals)]
    if not len(vals):
        return "Sin resultados en el rango."
    return f"En todo el rango el resultado va de <b>{vals.min():.0f}</b> a <b>{vals.max():.0f}</b> {unidad}."


def render() -> None:
    ui.page_header("Análisis de sensibilidad",
                   "¿Qué tan robustos son los resultados si los supuestos cambian?", "🧪")

    ui.seccion("Supuestos del modelo")
    st.caption("Valores de referencia para una tienda de autoservicio de tamaño medio. No son "
               "mediciones; cada uno se puede ajustar con datos reales en su módulo.")
    st.dataframe(SUPUESTOS, hide_index=True, use_container_width=True)

    ui.seccion("Cajas · ¿cuántas cajas necesito?")
    demandas = [80, 95, 110, 125, 140]
    tiempos = [2.0, 2.5, 3.0, 3.5]
    m_cajas = barrido_cajas(demandas, tiempos, REF["meta"])
    _mapa(m_cajas, f"Cajas mínimas para espera ≤ {REF['meta']:g} min",
          "Blues", "%{z:.0f}", "sens_cajas", invertir=True)
    ui.insight(_rango_texto(m_cajas, "cajas") + " Úsalo para dimensionar la dotación de "
               "hora pico con margen.")
    t_c = tornado_cajas()
    _tornado(t_c, float(t_c["Base"].iloc[0]), "¿Qué parámetro mueve más la espera en caja?",
             "min", "sens_tor_cajas")
    ui.insight(f"🔎 El parámetro que más mueve la espera es <b>{t_c.iloc[-1]['Parámetro']}</b>. "
               "Conviene medirlo con más cuidado antes de decidir.")

    ui.seccion("Estacionamiento · ¿cuántos autos no encuentran cajón?")
    autos = [50, 60, 70, 85, 100]
    cajones = [40, 50, 60, 70, 80]
    m_est = barrido_estacionamiento(autos, cajones, REF["estancia"])
    _mapa(m_est, "% de autos sin cajón (menos es mejor)", "Reds", "%{z:.1f}", "sens_est")
    ui.insight(f"🚗 Con los supuestos, el rechazo va de <b>{m_est.to_numpy().min():.1f}%</b> a "
               f"<b>{m_est.to_numpy().max():.1f}%</b>.")
    t_e = tornado_estacionamiento()
    _tornado(t_e, float(t_e["Base"].iloc[0]), "¿Qué parámetro mueve más el rechazo?",
             "%", "sens_tor_est")

    ui.seccion("Recibo · ¿cuántos andenes necesito?")
    camiones = [2, 3, 4, 6, 8]
    descargas = [30, 45, 60]
    m_and = barrido_andenes(camiones, descargas, REF["meta_r"])
    _mapa(m_and, f"Andenes mínimos para espera ≤ {REF['meta_r']:g} min",
          "Greens", "%{z:.0f}", "sens_and", invertir=True)
    ui.insight(_rango_texto(m_and, "andenes"))

    ui.seccion("Layout · ¿cuánto se ahorra al reubicar?")
    base = dict(layout.PARAM_DEFAULT)
    m_lay = barrido_layout([6, 8, 10, 12], [15, 20, 25], base)
    if m_lay.isna().all().all():
        st.info("Para este análisis primero carga la demostración desde el menú lateral.")
    else:
        _mapa(m_lay, "% de metros que se ahorran con la reubicación por rotación",
              "Greens", "%{z:.0f}", "sens_lay")
        vals = m_lay.to_numpy().ravel()
        vals = vals[~np.isnan(vals)]
        ui.insight(f"🧭 Con los datos actuales, reubicar por rotación ahorra entre "
                   f"<b>{vals.min():.0f}%</b> y <b>{vals.max():.0f}%</b> de los metros, según la "
                   "configuración del piso.")
