"""
Módulo 1 · Cuellos de botella y logística (Teoría de Restricciones)

Tres subsistemas de la tienda, analizados como colas:
    * Cajas            -> M/M/c (clientes que esperan turno en c cajas)
    * Estacionamiento  -> Erlang B (autos que llegan y no encuentran cajón)
    * Recibo           -> M/M/c (camiones que esperan un andén de descarga)

Herramientas:
    1. Cajas (colas)       -> utilización, espera, cajas mínimas, perfil horario y simulación.
    2. Estacionamiento     -> bloqueo, ocupación y ley de Little.
    3. Recibo              -> andenes necesarios para cumplir la meta de espera.
    4. Restricción (TOC)   -> cuál subsistema limita el flujo de la tienda y los 5 pasos.
    5. Datos observados    -> captura de tiempos reales y comparación por hora.
"""

from __future__ import annotations

import heapq
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from modulos import database as db
from modulos import ui

AREAS = ["Cajas", "Estacionamiento", "Recibo"]

# Clientes por hora típicos de una tienda de autoservicio (perfil de demanda)
PERFIL_CLIENTES = {
    7: 40, 8: 55, 9: 60, 10: 55, 11: 70, 12: 95, 13: 90, 14: 70,
    15: 65, 16: 75, 17: 100, 18: 110, 19: 95, 20: 80, 21: 60, 22: 35,
}

META_MAX_ESPERA_MIN = 30.0  # tope visual para gráficas


# =====================================================================
# Modelos de ingeniería
# =====================================================================
def mmc(lam_h: float, mu_h: float, c: int) -> dict:
    """
    Cola M/M/c (Erlang C).
    lam_h: llegadas por hora · mu_h: servicios por hora por servidor · c: servidores.
    Tiempos devueltos en minutos.
    """
    if lam_h <= 0:
        return {"rho": 0.0, "stable": True, "Pw": 0.0, "Wq": 0.0,
                "W": 60 / mu_h, "Lq": 0.0}
    a = lam_h / mu_h                  # carga ofrecida (Erlangs)
    rho = a / c                       # utilización por servidor
    if rho >= 1:
        return {"rho": rho, "stable": False, "Pw": 1.0, "Wq": math.inf,
                "W": math.inf, "Lq": math.inf}
    suma = sum(a ** k / math.factorial(k) for k in range(c))
    ultimo = a ** c / (math.factorial(c) * (1 - rho))
    p0 = 1 / (suma + ultimo)
    pw = ultimo * p0                  # probabilidad de tener que esperar
    lq = pw * rho / (1 - rho)         # clientes promedio en fila
    wq = lq / lam_h * 60              # Ley de Little: Lq = λ·Wq
    return {"rho": rho, "stable": True, "Pw": pw, "Wq": wq,
            "W": wq + 60 / mu_h, "Lq": lq}


def c_minimo(lam_h: float, mu_h: float, meta_min: float, rho_max: float = 0.85) -> int | None:
    """Menor número de servidores que cumple la meta de espera y una utilización máxima."""
    for c in range(1, 41):
        r = mmc(lam_h, mu_h, c)
        if r["stable"] and r["rho"] <= rho_max and r["Wq"] <= meta_min:
            return c
    return None


def erlang_b(a: float, n: int) -> float:
    """Probabilidad de bloqueo (sistema lleno) con n cajones y a Erlangs de carga."""
    if n <= 0:
        return 1.0
    b = 1.0
    for k in range(1, n + 1):
        b = a * b / (k + a * b)
    return b


def simular_espera(lam_h: float, servicio_min: float, c: int, horas: float = 1.0,
                   rng: np.random.Generator | None = None) -> np.ndarray:
    """
    Simulación de eventos discretos de una cola FCFS con c servidores.
    Llegadas Poisson y servicios exponenciales. Devuelve la espera de cada cliente (min).
    """
    rng = rng or np.random.default_rng()
    if lam_h <= 0 or c <= 0:
        return np.array([])
    n = rng.poisson(lam_h * horas)
    if n == 0:
        return np.array([])
    llegadas = np.sort(rng.uniform(0, horas * 60, n))   # minutos desde el inicio
    servicios = rng.exponential(servicio_min, n)
    libres = [0.0] * c                                  # instante en que cada servidor queda libre
    heapq.heapify(libres)
    esperas = np.empty(n)
    for i, (t_llega, t_serv) in enumerate(zip(llegadas, servicios)):
        t_libre = heapq.heappop(libres)                 # el servidor que antes se libera
        inicio = max(t_llega, t_libre)
        esperas[i] = inicio - t_llega
        heapq.heappush(libres, inicio + t_serv)
    return esperas


# =====================================================================
# Datos de demostración y persistencia
# =====================================================================
def generar_demo_toc(dias: int = 30, semilla: int | None = None) -> int:
    """Simula tiempos observados en cajas y recibo para los últimos días."""
    rng = np.random.default_rng(semilla)
    hoy = date.today()
    filas = []
    for d in range(dias):
        fecha = (hoy - timedelta(days=d)).isoformat()
        for hora, clientes in PERFIL_CLIENTES.items():
            lam = clientes * rng.uniform(0.9, 1.1)
            c = 5 if clientes >= 90 else (4 if clientes >= 65 else 3)
            espera = simular_espera(lam, 2.5, c, horas=1.0, rng=rng)
            if len(espera):
                muestra = rng.choice(espera, size=min(6, len(espera)), replace=False)
                filas += [(fecha, hora, "Cajas", round(float(m), 2), "demo") for m in muestra]
        espera_r = simular_espera(4, 45, 2, horas=4.0, rng=rng)
        if len(espera_r):
            muestra = rng.choice(espera_r, size=min(3, len(espera_r)), replace=False)
            filas += [(fecha, int(rng.integers(8, 16)), "Recibo", round(float(m), 2), "demo")
                      for m in muestra]
    db.executemany(
        "INSERT INTO tiempos_toc (fecha, hora, area, minutos, origen) VALUES (?, ?, ?, ?, ?)",
        filas,
    )
    return len(filas)


def obtener_tiempos() -> pd.DataFrame:
    return db.query_df("SELECT * FROM tiempos_toc ORDER BY fecha DESC, hora DESC, id DESC")


# =====================================================================
# Interfaz
# =====================================================================
def _parametros() -> dict:
    with st.expander("⚙️ Ajustes de la tienda", expanded=False):
        st.markdown("**🧾 Cajas**")
        c1, c2, c3, c4 = st.columns(4)
        cajas = c1.number_input("Cajas abiertas", min_value=1, max_value=20, value=5,
                                key="toc_cajas")
        t_caja = c2.number_input("Min. por cliente (servicio)", min_value=0.5, max_value=20.0,
                                 value=2.5, step=0.5, key="toc_tcaja")
        pico = c3.number_input("Clientes por hora (pico)", min_value=1, max_value=500,
                               value=110, key="toc_pico")
        meta = c4.number_input("Meta de espera en caja (min)", min_value=0.5, max_value=30.0,
                               value=3.0, step=0.5, key="toc_meta")

        st.markdown("**🚗 Estacionamiento**")
        e1, e2, e3 = st.columns(3)
        cajones = e1.number_input("Cajones disponibles", min_value=1, max_value=500, value=60,
                                  key="toc_cajones")
        llegadas_auto = e2.number_input("Autos que llegan por hora", min_value=0, max_value=1000,
                                        value=70, key="toc_autos")
        estancia = e3.number_input("Estancia promedio (min)", min_value=1.0, max_value=300.0,
                                   value=35.0, step=5.0, key="toc_estancia")

        st.markdown("**🚚 Recibo de proveedores**")
        r1, r2, r3, r4 = st.columns(4)
        andenes = r1.number_input("Andenes de descarga", min_value=1, max_value=20, value=2,
                                  key="toc_andenes")
        camiones = r2.number_input("Camiones por hora", min_value=0.0, max_value=50.0,
                                   value=4.0, step=0.5, key="toc_camiones")
        descarga = r3.number_input("Min. de descarga por camión", min_value=5.0,
                                   max_value=300.0, value=45.0, step=5.0, key="toc_descarga")
        meta_r = r4.number_input("Meta de espera en recibo (min)", min_value=1.0,
                                 max_value=120.0, value=30.0, step=5.0, key="toc_meta_r")
    return {
        "cajas": int(cajas), "t_caja": float(t_caja), "pico": float(pico), "meta": float(meta),
        "cajones": int(cajones), "llegadas_auto": float(llegadas_auto),
        "estancia": float(estancia),
        "andenes": int(andenes), "camiones": float(camiones), "descarga": float(descarga),
        "meta_r": float(meta_r),
    }


def _fmt_min(v: float) -> str:
    if v is None or not math.isfinite(v):
        return "∞ (inestable)"
    return f"{v:.1f} min"


def _tab_cajas(P: dict) -> None:
    mu = 60 / P["t_caja"]
    r = mmc(P["pico"], mu, P["cajas"])
    c_req = c_minimo(P["pico"], mu, P["meta"])

    k = st.columns(4)
    k[0].metric("Utilización de cajeros", f"{min(r['rho'], 9.99) * 100:.0f}%",
                "saturado" if r["rho"] >= 0.9 else "holgura" if r["rho"] < 0.7 else "normal",
                delta_color="off")
    k[1].metric("Espera promedio en fila", _fmt_min(r["Wq"]))
    k[2].metric("Probabilidad de hacer fila", f"{r['Pw'] * 100:.0f}%" if r["stable"] else "100%")
    k[3].metric("Cajas mínimas para la meta", f"{c_req}" if c_req else "No alcanzable",
                f"Tienes {P['cajas']}", delta_color="off")

    # Espera vs. número de cajas
    cs = list(range(1, 13))
    esperas = []
    for c in cs:
        v = mmc(P["pico"], mu, c)
        esperas.append(min(v["Wq"], META_MAX_ESPERA_MIN) if v["stable"] else np.nan)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cs, y=esperas, mode="lines+markers", name="Espera en fila",
                             line=dict(color=ui.COLOR_LINEA, width=3),
                             hovertemplate="%{x} cajas → %{y:.1f} min<extra></extra>"))
    fig.add_hline(y=P["meta"], line_dash="dash", line_color=ui.COLOR_A,
                  annotation_text=f"Meta: {P['meta']:g} min", annotation_position="top right")
    fig.add_vline(x=P["cajas"], line_dash="dot", line_color="gray",
                  annotation_text="Cajas actuales", annotation_position="bottom right")
    fig.update_layout(title=f"Espera según cajas abiertas (pico de {P['pico']:.0f} clientes/h)",
                      xaxis_title="Cajas abiertas", yaxis_title="Espera promedio (min)",
                      height=380, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, key="toc_fig_cajas_c")

    # Perfil horario: demanda vs. cajas necesarias
    horas = list(PERFIL_CLIENTES)
    req = [c_minimo(PERFIL_CLIENTES[h], mu, P["meta"]) for h in horas]
    req = [np.nan if v is None else v for v in req]
    fig_h = make_subplots(specs=[[{"secondary_y": True}]])
    fig_h.add_trace(go.Bar(x=[f"{h}:00" for h in horas], y=[PERFIL_CLIENTES[h] for h in horas],
                           name="Clientes por hora", marker_color="#90CAF9"), secondary_y=False)
    fig_h.add_trace(go.Scatter(x=[f"{h}:00" for h in horas], y=req, mode="lines+markers",
                               name="Cajas necesarias para la meta",
                               line=dict(color=ui.COLOR_A, width=3)), secondary_y=True)
    fig_h.add_trace(go.Scatter(x=[f"{h}:00" for h in horas], y=[P["cajas"]] * len(horas),
                               mode="lines", name="Cajas abiertas hoy",
                               line=dict(color="gray", dash="dot")), secondary_y=True)
    fig_h.update_layout(title="Perfil del día: demanda y cajas necesarias por hora", height=420,
                        margin=dict(l=10, r=10, t=50, b=10),
                        legend=dict(orientation="h", y=-0.2))
    fig_h.update_yaxes(title_text="Clientes/h", secondary_y=False)
    fig_h.update_yaxes(title_text="Cajas", secondary_y=True, dtick=1)
    st.plotly_chart(fig_h, key="toc_fig_perfil")

    horas_sobre = [h for h, q in zip(horas, req) if not np.isnan(q) and q > P["cajas"]]
    if horas_sobre:
        ui.insight(
            f"🔎 En <b>{len(horas_sobre)} horas</b> del día se necesitan más de {P['cajas']} cajas "
            f"para cumplir la meta de {P['meta']:g} min: "
            + ", ".join(f"<b>{h}:00</b>" for h in horas_sobre)
            + ". Abrir cajas en esas horas, en lugar de todo el día, es la mejora de menor costo."
        )
    else:
        ui.insight("✅ Con las cajas actuales se cumple la meta en todas las horas del perfil.")

    # Simulación de eventos discretos
    st.caption("Llegadas y servicios aleatorios. Con 8 horas o más, la espera simulada se "
               "acerca al modelo: esa convergencia valida el modelo.")
    horas_sim = st.slider("Horas simuladas", 1, 8, 1, key="toc_horas_sim")
    if st.button("▶️ Ejecutar simulación", key="toc_sim_btn"):
        st.session_state["toc_sim"] = simular_espera(P["pico"], P["t_caja"], P["cajas"],
                                                     float(horas_sim))
        st.session_state["toc_sim_horas"] = horas_sim
    esperas_sim = st.session_state.get("toc_sim")
    if esperas_sim is not None and len(esperas_sim):
        s = st.columns(4)
        s[0].metric("Clientes atendidos", f"{len(esperas_sim):,}")
        s[1].metric("Espera promedio (sim.)", _fmt_min(float(esperas_sim.mean())),
                    f"Modelo en estado estable: {_fmt_min(r['Wq'])}", delta_color="off")
        s[2].metric("Percentil 90", _fmt_min(float(np.percentile(esperas_sim, 90))))
        s[3].metric("Superan la meta", f"{(esperas_sim > P['meta']).mean() * 100:.0f}%",
                    delta_color="off")
        fig_s = px.histogram(x=esperas_sim, nbins=25,
                             labels={"x": "Espera en fila (min)", "count": "Clientes"},
                             title="Distribución de la espera simulada")
        fig_s.add_vline(x=P["meta"], line_dash="dash", line_color=ui.COLOR_A)
        fig_s.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        fig_s.update_traces(marker_color=ui.COLOR_LINEA)
        st.plotly_chart(fig_s, key="toc_fig_sim")


def _tab_estacionamiento(P: dict) -> None:
    a = P["llegadas_auto"] * P["estancia"] / 60          # carga ofrecida (autos ocupando cajón)
    bloqueo = erlang_b(a, P["cajones"])
    entran = P["llegadas_auto"] * (1 - bloqueo)
    ocupados = a * (1 - bloqueo)                          # promedio de cajones ocupados
    libres = P["cajones"] - ocupados
    perdidos = P["llegadas_auto"] * bloqueo

    st.markdown("#### Flujo vehicular · Erlang B y Ley de Little")
    k = st.columns(4)
    k[0].metric("Autos que no encuentran cajón", f"{bloqueo * 100:.1f}%",
                f"≈ {perdidos:.1f} autos/h", delta_color="inverse")
    k[1].metric("Cajones ocupados (promedio)", f"{ocupados:.0f} de {P['cajones']}")
    k[2].metric("Cajones libres (promedio)", f"{libres:.0f}")
    k[3].metric("Autos que sí entran por hora", f"{entran:.0f}")

    n_max = max(P["cajones"] * 2, 20)
    ns = list(range(1, n_max + 1))
    bl = [erlang_b(a, n) * 100 for n in ns]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ns, y=bl, mode="lines", line=dict(color=ui.COLOR_A, width=3),
                             name="% de autos sin cajón",
                             hovertemplate="%{x} cajones → %{y:.1f}%<extra></extra>"))
    fig.add_vline(x=P["cajones"], line_dash="dot", line_color="gray",
                  annotation_text="Cajones actuales", annotation_position="top right")
    fig.add_hline(y=5, line_dash="dash", line_color=ui.COLOR_B,
                  annotation_text="Tolerancia 5 %", annotation_position="bottom right")
    fig.update_layout(title="Autos sin cajón según el número de cajones", height=380,
                      xaxis_title="Cajones", yaxis_title="% de autos que no entran",
                      margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, key="toc_fig_estac")

    if bloqueo > 0.05:
        n_req = next((n for n in ns if erlang_b(a, n) <= 0.05), None)
        ui.insight(f"🚗 Más del 5 % de los autos no encuentra cajón. Para bajarlo a 5 % se "
                   f"necesitan <b>{n_req} cajones</b> (hoy tienes {P['cajones']}). Antes de "
                   "construir más, revisa si la estancia promedio puede reducirse con señalización "
                   "y control de accesos.")
    else:
        ui.insight("✅ El estacionamiento absorbe la demanda con menos de 5 % de rechazo.")
    st.caption("Ley de Little: ocupación promedio = autos que entran por hora × estancia "
               f"({entran:.0f} × {P['estancia']:.0f} min ÷ 60 = {entran * P['estancia'] / 60:.1f} "
               "cajones).")


def _tab_recibo(P: dict) -> None:
    mu = 60 / P["descarga"]
    r = mmc(P["camiones"], mu, P["andenes"])
    req = c_minimo(P["camiones"], mu, P["meta_r"])

    st.markdown("#### Recibo de proveedores · andenes de descarga")
    k = st.columns(4)
    k[0].metric("Utilización de andenes", f"{min(r['rho'], 9.99) * 100:.0f}%")
    k[1].metric("Espera promedio del camión", _fmt_min(r["Wq"]))
    k[2].metric("Tiempo total en el andén", _fmt_min(r["W"]))
    k[3].metric("Andenes necesarios para la meta", f"{req}" if req else "No alcanzable",
                f"Tienes {P['andenes']}", delta_color="off")

    ans = list(range(1, 9))
    esperas = []
    for n in ans:
        v = mmc(P["camiones"], mu, n)
        esperas.append(min(v["Wq"], META_MAX_ESPERA_MIN * 2) if v["stable"] else np.nan)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ans, y=esperas, mode="lines+markers", name="Espera",
                             line=dict(color=ui.COLOR_PRIMARIO, width=3)))
    fig.add_hline(y=P["meta_r"], line_dash="dash", line_color=ui.COLOR_A,
                  annotation_text=f"Meta: {P['meta_r']:g} min", annotation_position="top right")
    fig.add_vline(x=P["andenes"], line_dash="dot", line_color="gray",
                  annotation_text="Andenes actuales", annotation_position="bottom right")
    fig.update_layout(title="Espera del camión según andenes", height=360,
                      xaxis_title="Andenes de descarga", yaxis_title="Espera (min)",
                      xaxis=dict(dtick=1), margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, key="toc_fig_recibo")

    if req and req > P["andenes"]:
        ui.insight(f"🚚 Con {P['andenes']} andén(es) los camiones esperan {_fmt_min(r['Wq'])}. "
                   f"Se requieren <b>{req} andenes</b> o programar citas de llegada para repartir "
                   "la carga a lo largo del día.")
    else:
        ui.insight("✅ Los andenes actuales cumplen la meta de espera de descarga.")


def _tab_restriccion(P: dict) -> None:
    cap_c = P["cajas"] * 60 / P["t_caja"]
    dem_c = P["pico"]
    cap_e = P["cajones"] * 60 / P["estancia"]
    dem_e = P["llegadas_auto"]
    cap_r = P["andenes"] * 60 / P["descarga"]
    dem_r = P["camiones"]

    sistemas = pd.DataFrame([
        {"Subsistema": "Cajas", "Demanda (por h)": dem_c, "Capacidad (por h)": cap_c,
         "Unidad": "clientes"},
        {"Subsistema": "Estacionamiento", "Demanda (por h)": dem_e, "Capacidad (por h)": cap_e,
         "Unidad": "autos"},
        {"Subsistema": "Recibo", "Demanda (por h)": dem_r, "Capacidad (por h)": cap_r,
         "Unidad": "camiones"},
    ])
    sistemas["Carga relativa"] = sistemas["Demanda (por h)"] / sistemas["Capacidad (por h)"]
    top = sistemas.loc[sistemas["Carga relativa"].idxmax()]

    st.markdown("#### Teoría de Restricciones · ¿qué limita el flujo?")
    st.caption("Carga relativa = demanda ÷ capacidad. El subsistema con mayor carga es la "
               "restricción: limita todo el flujo de la tienda aunque los demás tengan holgura. "
               "Las cifras de cada subsistema tienen unidades distintas, por eso se comparan "
               "como porcentaje.")
    colores = [ui.COLOR_A if s == top["Subsistema"] else ui.COLOR_C
               for s in sistemas["Subsistema"]]
    fig = go.Figure(go.Bar(
        x=sistemas["Subsistema"], y=sistemas["Carga relativa"] * 100,
        marker_color=colores,
        text=[f"{v * 100:.0f}%" for v in sistemas["Carga relativa"]], textposition="outside",
    ))
    fig.add_hline(y=100, line_dash="dash", line_color="black",
                  annotation_text="Capacidad al límite", annotation_position="top left")
    fig.update_layout(title="Carga relativa por subsistema", height=380,
                      yaxis_title="% de la capacidad usada", yaxis_range=[0, max(
                          120, float(sistemas["Carga relativa"].max() * 100) * 1.2)],
                      margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, key="toc_fig_restr")

    tabla = sistemas.copy()
    tabla["Carga relativa"] = (tabla["Carga relativa"] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(tabla.round(1), hide_index=True)

    if top["Carga relativa"] >= 1:
        ui.insight(f"🚨 <b>{top['Subsistema']}</b> supera su capacidad "
                   f"({top['Carga relativa'] * 100:.0f}%). Es la restricción: mientras no se "
                   "resuelva, el resto del sistema no puede producir más flujo.")
    else:
        ui.insight(f"🎯 La restricción actual es <b>{top['Subsistema']}</b>, con "
                   f"{top['Carga relativa'] * 100:.0f}% de su capacidad usada. Las mejoras "
                   "deben concentrarse ahí.")

    st.markdown("##### Los 5 pasos de la Teoría de Restricciones")
    pasos = [
        ("1. Identificar", f"Confirma que la restricción es **{top['Subsistema']}** con datos "
                           "observados, no con suposiciones."),
        ("2. Explotar", "Usa al máximo lo que ya tienes: cajas abiertas en horas pico, "
                        "cajones con control de rotación, citas de descarga."),
        ("3. Subordinar", "Ajusta el resto del sistema al ritmo de la restricción: no "
                          "sobreproduzcas en otras áreas."),
        ("4. Elevar", "Invierte en capacidad de la restricción: más cajas, cajones o andenes "
                      "si los pasos anteriores no bastan."),
        ("5. Repetir", "Cuando se rompa la restricción, aparecerá otra. Vuelve al paso 1."),
    ]
    for titulo, texto in pasos:
        st.markdown(f"**{titulo}** · {texto}")


def _tab_datos() -> None:
    df = obtener_tiempos()

    st.markdown("#### Registrar tiempo observado")
    with st.form("form_toc", clear_on_submit=True):
        f1, f2, f3, f4 = st.columns(4)
        fecha = f1.date_input("Fecha", value=date.today(), max_value=date.today(),
                              format="DD/MM/YYYY")
        hora = f2.number_input("Hora (0–23)", min_value=0, max_value=23, value=18)
        area = f3.selectbox("Área", AREAS)
        minutos = f4.number_input("Minutos observados", min_value=0.0, max_value=600.0,
                                  value=3.0, step=0.5)
        if st.form_submit_button("Guardar tiempo", type="primary"):
            db.execute(
                "INSERT INTO tiempos_toc (fecha, hora, area, minutos, origen) "
                "VALUES (?, ?, ?, ?, 'manual')",
                (fecha.isoformat(), int(hora), area, float(minutos)),
            )
            st.success("Tiempo registrado.")
            st.rerun()

    if df.empty:
        st.info("Aún no hay tiempos observados. Registra algunos o carga la demostración.")
        if st.button("🎲 Cargar 30 días de tiempos simulados", type="primary"):
            n = generar_demo_toc()
            st.session_state["toc_flash"] = f"Se cargaron {n} tiempos de demostración."
            st.rerun()
        return

    resumen = (df.groupby("area")["minutos"]
               .agg(n="count", promedio="mean", p90=lambda s: s.quantile(0.9))
               .reset_index())
    st.markdown("#### Resumen por área")
    cols = st.columns(len(resumen))
    for col, (_, fila) in zip(cols, resumen.iterrows()):
        col.metric(fila["area"], f"{fila['promedio']:.1f} min",
                   f"P90 {fila['p90']:.1f} min · n={int(fila['n']):,}", delta_color="off")

    por_hora = df.groupby(["area", "hora"], as_index=False)["minutos"].mean()
    fig = px.line(por_hora, x="hora", y="minutos", color="area", markers=True,
                  title="Espera promedio observada por hora",
                  labels={"hora": "Hora del día", "minutos": "Minutos", "area": "Área"})
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, key="toc_fig_datos")

    st.dataframe(df.head(300), hide_index=True, height=320)
    a1, a2 = st.columns(2)
    if a1.button("🎲 Agregar 30 días de tiempos simulados"):
        n = generar_demo_toc()
        st.session_state["toc_flash"] = f"Se cargaron {n} tiempos de demostración."
        st.rerun()
    confirmar = a2.checkbox("Confirmo que quiero borrar todos los tiempos de este módulo",
                            key="toc_conf")
    if a2.button("Borrar tiempos", disabled=not confirmar):
        db.execute("DELETE FROM tiempos_toc")
        st.session_state["toc_flash"] = "Se borraron los tiempos observados."
        st.rerun()


# =====================================================================
# Punto de entrada
# =====================================================================
def render() -> None:
    ui.page_header(
        "Cuellos de Botella y Logística",
        "Teoría de Restricciones · Colas M/M/c · Erlang B · Simulación de eventos discretos",
        "🚦",
    )
    if "toc_flash" in st.session_state:
        st.success(st.session_state.pop("toc_flash"))

    P = _parametros()
    ui.seccion("🧾 Cajas · espera en fila")
    _tab_cajas(P)
    ui.seccion("🚗 Estacionamiento")
    _tab_estacionamiento(P)
    ui.seccion("🚚 Recibo de proveedores")
    _tab_recibo(P)
    ui.seccion("🎯 Restricción · ¿qué limita la tienda?")
    _tab_restriccion(P)
    ui.seccion("📋 Tiempos observados")
    _tab_datos()
