"""
Módulo 4 · Cuadro de Mando Kaizen (KPIs por turno)

Indicadores por turno, calculados a partir de la producción registrada:
    * Cumplimiento de meta    = transacciones reales ÷ meta × 100
    * Productividad           = transacciones ÷ (colaboradores × horas)
    * Eficiencia operativa    = tiempo productivo ÷ tiempo planeado × 100
    * Tiempos muertos         = minutos no productivos, con Pareto por causa
    * Semáforo (Andon)        = Verde / Amarillo / Rojo según umbrales configurables

Pestañas:
    1. Panel del día   -> semáforo por turno, medidores y resumen del día.
    2. Tendencias      -> cumplimiento y productividad por día y turno.
    3. Tiempos muertos -> Pareto de causas y mapa de calor turno × causa.
    4. Registro        -> captura diaria, carga de demostración y administración.
    5. Kaizen          -> bitácora de mejoras implementadas y su resultado.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from modulos import database as db
from modulos import ui
from modulos.catalogos import MOTIVOS_MUERTO, TURNOS

METAS_DEFAULT = {TURNOS[0]: 900, TURNOS[1]: 1100, TURNOS[2]: 500}
COLAB_DEFAULT = {TURNOS[0]: 8, TURNOS[1]: 10, TURNOS[2]: 5}
HORAS_TURNO = 8.0

COLOR_SEMAFORO = {"Verde": ui.COLOR_PRIMARIO, "Amarillo": ui.COLOR_B, "Rojo": ui.COLOR_A}


# =====================================================================
# Datos
# =====================================================================
def _corto(turno: str) -> str:
    return turno.split(" ")[0]


def calcular_kpis(df: pd.DataFrame, umbral_verde: float, umbral_amarillo: float,
                  efic_verde: float) -> pd.DataFrame:
    """Agrega KPIs y el semáforo a cada registro de producción."""
    if df.empty:
        return df
    d = df.copy()
    d["fecha"] = pd.to_datetime(d["fecha"])
    d["turno_corto"] = d["turno"].map(_corto)
    d["cumplimiento"] = d["real"] / d["meta"].replace(0, np.nan) * 100
    d["productividad"] = d["real"] / (d["colaboradores"] * d["horas"]).replace(0, np.nan)
    tiempo_plan = d["horas"] * 60
    d["eficiencia"] = (tiempo_plan - d["minutos_muertos"]) / tiempo_plan.replace(0, np.nan) * 100

    def color(fila):
        if fila["cumplimiento"] >= umbral_verde and fila["eficiencia"] >= efic_verde:
            return "Verde"
        if fila["cumplimiento"] >= umbral_amarillo:
            return "Amarillo"
        return "Rojo"

    d["semaforo"] = d.apply(color, axis=1)
    return d


def cargar(desde: date, hasta: date, umbrales: dict) -> pd.DataFrame:
    df = db.query_df(
        "SELECT * FROM produccion_turnos WHERE fecha BETWEEN ? AND ? ORDER BY fecha, turno",
        (desde.isoformat(), hasta.isoformat()),
    )
    return calcular_kpis(df, umbrales["verde"], umbrales["amarillo"], umbrales["efic"])


def _upsert(fila: dict) -> None:
    db.execute(
        """INSERT INTO produccion_turnos (fecha, turno, meta, real, colaboradores, horas,
               minutos_muertos, motivo_muerto, origen)
           VALUES (:fecha, :turno, :meta, :real, :colaboradores, :horas,
                   :minutos_muertos, :motivo_muerto, :origen)
           ON CONFLICT (fecha, turno) DO UPDATE SET
               meta = excluded.meta, real = excluded.real,
               colaboradores = excluded.colaboradores, horas = excluded.horas,
               minutos_muertos = excluded.minutos_muertos,
               motivo_muerto = excluded.motivo_muerto, origen = excluded.origen""",
        fila,
    )


def generar_demo_kaizen(dias: int = 45, semilla: int | None = None) -> int:
    """Turnos con desempeño distinto: el matutino cumple, el nocturno tiene más paros."""
    rng = np.random.default_rng(semilla)
    hoy = date.today()
    perfil = {
        TURNOS[0]: dict(f=1.04, sd=0.05, paro=40, colab=COLAB_DEFAULT[TURNOS[0]]),
        TURNOS[1]: dict(f=0.98, sd=0.06, paro=65, colab=COLAB_DEFAULT[TURNOS[1]]),
        TURNOS[2]: dict(f=0.90, sd=0.08, paro=95, colab=COLAB_DEFAULT[TURNOS[2]]),
    }
    pesos_motivo = np.array([0.30, 0.25, 0.20, 0.12, 0.08, 0.05])
    pesos_motivo = pesos_motivo / pesos_motivo.sum()
    n = 0
    for d in range(dias):
        dia = hoy - timedelta(days=d)
        bonus = 1.07 if dia.weekday() >= 4 else 1.0   # viernes a domingo se vende más
        for turno in TURNOS:
            p = perfil[turno]
            meta = METAS_DEFAULT[turno]
            real = max(0.0, meta * p["f"] * bonus * rng.normal(1.0, p["sd"]))
            paro = max(0.0, rng.normal(p["paro"], p["paro"] * 0.3))
            _upsert({
                "fecha": dia.isoformat(), "turno": turno, "meta": float(meta),
                "real": round(float(real), 0), "colaboradores": int(p["colab"]),
                "horas": HORAS_TURNO, "minutos_muertos": round(float(paro), 1),
                "motivo_muerto": str(rng.choice(MOTIVOS_MUERTO, p=pesos_motivo)),
                "origen": "demo",
            })
            n += 1
    if db.contar("eventos_kaizen") == 0:
        eventos = [
            (hoy - timedelta(days=30), TURNOS[2], "Reabasto por zonas en vez de ronda única",
             "Espera de mercancía o reabasto", "Dividir la tienda en 3 zonas con responsable fijo",
             "Espera de reabasto bajó de 25 a 10 min por turno", "Gerente de turno"),
            (hoy - timedelta(days=18), TURNOS[1], "Checklist de arranque de cajas",
             "Falla de equipo (cajas, básculas, lector)", "Revisar lector y báscula antes de las 15 h",
             "Fallas de equipo reducidas 40 %", "Supervisor de cajas"),
            (hoy - timedelta(days=7), TURNOS[0], "5S en área de perecederos",
             "Limpieza o derrames", "Señalizar zonas y rutina de limpieza de 5 min",
             "Limpieza fuera del horario pico", "Encargado de perecederos"),
        ]
        db.executemany(
            """INSERT INTO eventos_kaizen (fecha, turno, titulo, causa, accion, resultado,
               responsable) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(f.isoformat(), t, ti, c, a, r, res) for f, t, ti, c, a, r, res in eventos],
        )
    return n


# =====================================================================
# Visualización
# =====================================================================
def _badge(color: str) -> str:
    return {"Verde": ":green-badge[🟢 Verde]", "Amarillo": ":orange-badge[🟡 Amarillo]",
            "Rojo": ":red-badge[🔴 Rojo]"}[color]


def _medidor(valor: float, titulo: str, meta: float, key: str) -> None:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=0 if np.isnan(valor) else valor,
        number={"suffix": "%", "valueformat": ".0f"},
        title={"text": titulo},
        gauge={
            "axis": {"range": [0, 120]},
            "bar": {"color": ui.COLOR_LINEA},
            "steps": [{"range": [0, 90], "color": "rgba(198,40,40,.18)"},
                      {"range": [90, 100], "color": "rgba(239,143,0,.18)"},
                      {"range": [100, 120], "color": "rgba(46,125,50,.18)"}],
            "threshold": {"line": {"color": "black", "width": 3}, "value": meta},
        },
    ))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=40, b=0))
    st.plotly_chart(fig, key=key)


def _pareto_paros(df: pd.DataFrame) -> go.Figure:
    mot = (df.groupby("motivo_muerto", as_index=False)["minutos_muertos"].sum()
           .sort_values("minutos_muertos", ascending=False).reset_index(drop=True))
    mot["pct"] = mot["minutos_muertos"] / mot["minutos_muertos"].sum() * 100
    mot["acum"] = mot["pct"].cumsum()
    previo = mot["acum"] - mot["pct"]
    mot["clase"] = np.where(previo < 80, "A", "B/C")
    colores = mot["clase"].map({"A": ui.COLOR_A, "B/C": ui.COLOR_C})
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=mot["motivo_muerto"], y=mot["minutos_muertos"], marker_color=colores,
                         name="Minutos perdidos",
                         text=[f"{v:,.0f} min" for v in mot["minutos_muertos"]],
                         textposition="outside", cliponaxis=False), secondary_y=False)
    fig.add_trace(go.Scatter(x=mot["motivo_muerto"], y=mot["acum"], mode="lines+markers",
                             name="% acumulado", line=dict(color=ui.COLOR_LINEA, width=2.5)),
                  secondary_y=True)
    fig.add_hline(y=80, line_dash="dash", line_color=ui.COLOR_A, secondary_y=True)
    fig.update_yaxes(title_text="Minutos", secondary_y=False,
                     range=[0, mot["minutos_muertos"].max() * 1.2])
    fig.update_yaxes(title_text="% acumulado", secondary_y=True, range=[0, 105], ticksuffix="%")
    fig.update_xaxes(tickangle=-25)
    fig.update_layout(title="Pareto de tiempos muertos por causa", height=440,
                      margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=1.1))
    return fig


# =====================================================================
# Interfaz
# =====================================================================
def _parametros() -> dict:
    with st.expander("⚙️ Metas y umbrales del semáforo", expanded=False):
        st.markdown("**Metas de transacciones por turno**")
        cols = st.columns(3)
        metas = {}
        for col, turno in zip(cols, TURNOS):
            metas[turno] = col.number_input(_corto(turno), min_value=1, max_value=10000,
                                            value=METAS_DEFAULT[turno], step=50,
                                            key=f"kz_meta_{_corto(turno)}")
        st.markdown("**Umbrales del semáforo**")
        u1, u2, u3 = st.columns(3)
        verde = u1.number_input("Verde: cumplimiento mínimo (%)", 50, 150, 100, key="kz_verde")
        amarillo = u2.number_input("Amarillo: cumplimiento mínimo (%)", 50, 150, 90,
                                   key="kz_amarillo")
        efic = u3.number_input("Verde: eficiencia mínima (%)", 50, 100, 90, key="kz_efic")
    return {"metas": metas, "verde": float(verde), "amarillo": float(amarillo),
            "efic": float(efic)}


def _tab_panel(P: dict, umbrales: dict) -> None:
    hoy = date.today()
    ultima = db.query_df("SELECT MAX(fecha) AS f FROM produccion_turnos")["f"].iloc[0]
    fecha_ref = date.fromisoformat(ultima) if ultima else hoy
    f = st.date_input("Día a revisar", value=fecha_ref, max_value=hoy, format="DD/MM/YYYY",
                      key="kz_dia")
    df = cargar(f, f, umbrales)

    if df.empty:
        st.info(f"No hay registros de producción para el {f:%d/%m/%Y}. Captúralos en "
                "**Registro** o carga la demostración.")
        return

    cols = st.columns(len(TURNOS))
    for col, turno in zip(cols, TURNOS):
        with col.container(border=True):
            fila = df[df["turno"] == turno]
            st.markdown(f"##### {_corto(turno)}")
            if fila.empty:
                st.caption("Sin registro")
                continue
            r = fila.iloc[0]
            st.markdown(_badge(r["semaforo"]))
            st.metric("Cumplimiento", f"{r['cumplimiento']:.0f}%",
                      f"{r['real']:,.0f} de {r['meta']:,.0f}", delta_color="off")
            st.metric("Eficiencia", f"{r['eficiencia']:.0f}%",
                      f"{r['minutos_muertos']:.0f} min muertos", delta_color="off")
            st.metric("Productividad", f"{r['productividad']:.1f} trans./h-persona",
                      delta_color="off")
            st.caption(f"Paro principal: {r['motivo_muerto'] or 'sin especificar'}")

    g1, g2 = st.columns(2)
    with g1:
        _medidor(float(df["cumplimiento"].mean()), "Cumplimiento promedio del día", 100,
                 "kz_g_cumpl")
    with g2:
        _medidor(float(df["eficiencia"].mean()), "Eficiencia operativa del día", 90, "kz_g_efic")

    peor = df.loc[df["cumplimiento"].idxmin()]
    mejor = df.loc[df["cumplimiento"].idxmax()]
    rojos = (df["semaforo"] == "Rojo").sum()
    ui.insight(
        f"🔎 Mejor turno: <b>{_corto(mejor['turno'])}</b> ({mejor['cumplimiento']:.0f}%). "
        f"Mayor brecha: <b>{_corto(peor['turno'])}</b> ({peor['cumplimiento']:.0f}%), con "
        f"{peor['minutos_muertos']:.0f} min muertos, sobre todo por "
        f"<b>{peor['motivo_muerto'] or 'causas no especificadas'}</b>. "
        f"{rojos} turno(s) en rojo."
    )


def _tab_tendencias(umbrales: dict) -> None:
    dias = st.slider("Días a analizar", 7, 60, 30, key="kz_dias")
    hasta = date.today()
    desde = hasta - timedelta(days=dias - 1)
    df = cargar(desde, hasta, umbrales)
    if df.empty:
        st.info("Sin datos en el periodo seleccionado.")
        return

    c1 = px.line(df, x="fecha", y="cumplimiento", color="turno_corto", markers=True,
                 title="Cumplimiento de meta por día (%)",
                 labels={"fecha": "", "cumplimiento": "%", "turno_corto": "Turno"},
                 color_discrete_sequence=[ui.COLOR_LINEA, ui.COLOR_B, ui.COLOR_A])
    c1.add_hline(y=100, line_dash="dash", line_color=ui.COLOR_PRIMARIO)
    c1.add_hline(y=90, line_dash="dot", line_color=ui.COLOR_B)
    c1.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10),
                     legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(c1, key="kz_fig_cumpl")

    c2 = px.line(df, x="fecha", y="eficiencia", color="turno_corto", markers=True,
                 title="Eficiencia operativa por día (%)",
                 labels={"fecha": "", "eficiencia": "%", "turno_corto": "Turno"},
                 color_discrete_sequence=[ui.COLOR_LINEA, ui.COLOR_B, ui.COLOR_A])
    c2.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10),
                     legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(c2, key="kz_fig_efic")

    resumen = (df.groupby("turno_corto")
               .agg(cumplimiento=("cumplimiento", "mean"), eficiencia=("eficiencia", "mean"),
                    productividad=("productividad", "mean"),
                    rojos=("semaforo", lambda s: (s == "Rojo").sum()))
               .reset_index())
    st.markdown("##### Resumen del periodo")
    st.dataframe(
        resumen, hide_index=True,
        column_config={
            "turno_corto": "Turno",
            "cumplimiento": st.column_config.ProgressColumn(
                "Cumplimiento", format="%.0f%%", min_value=0, max_value=120),
            "eficiencia": st.column_config.NumberColumn("Eficiencia", format="%.1f%%"),
            "productividad": st.column_config.NumberColumn("Trans./h-persona", format="%.1f"),
            "rojos": st.column_config.NumberColumn("Días en rojo"),
        },
    )

    mejora = (df.assign(sem=df["semaforo"] == "Verde")
              .groupby("turno_corto")["sem"].mean() * 100)
    if mejora.size:
        ui.insight(f"📈 Porcentaje de días en verde del periodo: "
                   + ", ".join(f"<b>{t}</b> {v:.0f}%" for t, v in mejora.items()) + ".")


def _tab_paros(umbrales: dict) -> None:
    hasta = date.today()
    desde = hasta - timedelta(days=29)
    df = cargar(desde, hasta, umbrales)
    if df.empty or df["minutos_muertos"].sum() == 0:
        st.info("Sin tiempos muertos registrados en los últimos 30 días.")
        return

    total_min = df["minutos_muertos"].sum()
    plan_min = (df["horas"] * 60).sum()
    k = st.columns(3)
    k[0].metric("Minutos muertos (30 días)", f"{total_min:,.0f}")
    k[1].metric("Tiempo muerto del total planeado", f"{total_min / plan_min * 100:.1f}%")
    k[2].metric("Causa principal", df.groupby("motivo_muerto")["minutos_muertos"].sum()
                .idxmax())

    st.plotly_chart(_pareto_paros(df), key="kz_fig_paros")

    mapa = df.pivot_table(index="turno_corto", columns="motivo_muerto",
                          values="minutos_muertos", aggfunc="sum", fill_value=0)
    fig = px.imshow(mapa, text_auto=".0f", aspect="auto", color_continuous_scale="Reds",
                    title="Mapa de calor: turno × causa de tiempo muerto (min)")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10), xaxis_title="",
                      yaxis_title="")
    st.plotly_chart(fig, key="kz_fig_calor")


def _tab_registro(P: dict) -> None:
    st.markdown("#### Registrar producción de un turno")
    with st.form("form_kaizen", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        fecha = f1.date_input("Fecha", value=date.today(), max_value=date.today(),
                              format="DD/MM/YYYY")
        turno = f2.selectbox("Turno", TURNOS, format_func=_corto)
        meta = f3.number_input("Meta de transacciones", min_value=1.0,
                               value=float(P["metas"][turno]), step=10.0)
        g1, g2, g3 = st.columns(3)
        real = g1.number_input("Transacciones realizadas", min_value=0.0, value=0.0, step=10.0)
        colab = g2.number_input("Colaboradores en turno", min_value=1, value=COLAB_DEFAULT[turno])
        horas = g3.number_input("Horas planeadas", min_value=1.0, max_value=12.0,
                                value=HORAS_TURNO, step=0.5)
        h1, h2 = st.columns(2)
        paro = h1.number_input("Minutos muertos", min_value=0.0, value=0.0, step=5.0)
        motivo = h2.selectbox("Causa principal del tiempo muerto", MOTIVOS_MUERTO)
        enviado = st.form_submit_button("💾 Guardar turno", type="primary")

    if enviado:
        if paro > horas * 60:
            st.error("Los minutos muertos no pueden superar el tiempo del turno.")
        else:
            _upsert({"fecha": fecha.isoformat(), "turno": turno, "meta": float(meta),
                     "real": float(real), "colaboradores": int(colab), "horas": float(horas),
                     "minutos_muertos": float(paro), "motivo_muerto": motivo,
                     "origen": "manual"})
            st.session_state["kz_flash"] = (
                f"Turno {_corto(turno)} del {fecha:%d/%m} guardado (si ya existía, se actualizó).")
            st.rerun()

    st.markdown("#### Administración")
    a1, a2 = st.columns(2)
    if a1.button("🎲 Cargar 45 días de producción simulada"):
        n = generar_demo_kaizen()
        st.session_state["kz_flash"] = f"Se cargaron {n} turnos de demostración."
        st.rerun()
    confirmar = a2.checkbox("Confirmo borrar toda la producción de este módulo", key="kz_conf")
    if a2.button("Borrar producción", disabled=not confirmar):
        db.execute("DELETE FROM produccion_turnos")
        st.session_state["kz_flash"] = "Se borró la producción registrada."
        st.rerun()

    with st.expander("🗂️ Últimos registros"):
        ult = db.query_df("SELECT fecha, turno, meta, real, colaboradores, horas, "
                          "minutos_muertos, motivo_muerto, origen FROM produccion_turnos "
                          "ORDER BY fecha DESC, turno LIMIT 200")
        st.dataframe(ult, hide_index=True, height=340)


def _tab_kaizen() -> None:
    st.markdown("#### Registrar una mejora Kaizen")
    with st.form("form_evento", clear_on_submit=True):
        e1, e2, e3 = st.columns(3)
        fecha = e1.date_input("Fecha", value=date.today(), max_value=date.today(),
                              format="DD/MM/YYYY", key="ev_fecha")
        turno = e2.selectbox("Turno", ["Todos"] + TURNOS, format_func=lambda t: t if t == "Todos"
                             else _corto(t), key="ev_turno")
        responsable = e3.text_input("Responsable")
        titulo = st.text_input("Título de la mejora *", placeholder="Ej. Reabasto por zonas")
        c1, c2 = st.columns(2)
        causa = c1.selectbox("Causa que se atacó", MOTIVOS_MUERTO)
        accion = c2.text_input("Acción implementada *",
                               placeholder="Ej. Dividir la tienda en 3 zonas")
        resultado = st.text_area("Resultado medido", height=70,
                                 placeholder="Ej. Espera de reabasto bajó de 25 a 10 min.")
        if st.form_submit_button("Guardar mejora", type="primary"):
            if not titulo.strip() or not accion.strip():
                st.error("Escribe el título y la acción implementada.")
            else:
                db.execute(
                    """INSERT INTO eventos_kaizen (fecha, turno, titulo, causa, accion, resultado,
                       responsable) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (fecha.isoformat(), None if turno == "Todos" else turno, titulo.strip(),
                     causa, accion.strip(), resultado.strip(), responsable.strip()),
                )
                st.session_state["kz_flash"] = "Mejora Kaizen registrada."
                st.rerun()

    eventos = db.query_df("SELECT * FROM eventos_kaizen ORDER BY fecha DESC, id DESC")
    if eventos.empty:
        st.info("Aún no hay mejoras registradas. Cada mejora conectada a un paro medible "
                "es una prueba de la metodología PHVA en la tesis.")
        return
    st.markdown(f"#### Bitácora · {len(eventos)} mejoras")
    st.dataframe(
        eventos.drop(columns=["id", "creado_en"]), hide_index=True,
        column_config={
            "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "turno": "Turno", "titulo": "Mejora", "causa": "Causa atacada",
            "accion": "Acción", "resultado": "Resultado", "responsable": "Responsable",
        },
    )


# =====================================================================
# Punto de entrada
# =====================================================================
def render() -> None:
    ui.page_header(
        "Cuadro de Mando Kaizen",
        "KPIs por turno · cumplimiento de meta · eficiencia operativa · tiempos muertos · semáforo",
        "🎯",
    )
    if "kz_flash" in st.session_state:
        st.success(st.session_state.pop("kz_flash"))

    P = _parametros()
    umbrales = {"verde": P["verde"], "amarillo": P["amarillo"], "efic": P["efic"]}
    t1, t2, t3, t4, t5 = st.tabs(["🚦 Panel del día", "📈 Tendencias", "⏱️ Tiempos muertos",
                                  "📝 Registro", "💡 Kaizen"])
    with t1:
        _tab_panel(P, umbrales)
    with t2:
        _tab_tendencias(umbrales)
    with t3:
        _tab_paros(umbrales)
    with t4:
        _tab_registro(P)
    with t5:
        _tab_kaizen()
