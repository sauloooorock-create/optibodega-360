"""
Módulo 3 · Optimización de layout y recorridos

Modelo del piso de venta (en metros):
    * El almacén central está en el origen (0, 0).
    * Un pasillo principal corre por y = 0 y de él salen los pasillos de venta.
    * Cada producto está en un pasillo p y a una posición y sobre ese pasillo.

Distancia rectilínea (Manhattan sobre la red de pasillos):
    * Mismo pasillo:       |y1 - y2|
    * Pasillos distintos:  y1 + |x1 - x2| + y2   (bajar al pasillo principal, cruzar y subir)

Herramientas:
    1. Plano y ruta       -> ruta de surtido: actual vs. vecino más cercano vs. 2-opt.
    2. Distancias         -> distancia de cada pasillo y cada producto al almacén.
    3. Rotación (ABC)     -> reubicación por frecuencia de surtido y ahorro de recorrido.
    4. Operaciones        -> diagrama de operaciones y recorrido (ASME) con tiempos.
    5. Datos              -> ubicaciones editables y demostración.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modulos import database as db
from modulos import ui

OFFSET_M = 4.0           # distancia del almacén al primer pasillo de venta (m)
ORIGEN = (0.0, 0.0, "Almacén")
PARAM_DEFAULT = {"pasillos": 8, "largo": 20.0, "sep": 5.0, "vel": 1.2, "pick": 0.3}
SIMBOLOS = {"Operación": "○", "Transporte": "→", "Inspección": "□", "Demora": "D"}


# =====================================================================
# Geometría y distancias
# =====================================================================
def x_pasillo(p: int, sep: float) -> float:
    return OFFSET_M + (p - 1) * sep


def dist(a: tuple, b: tuple) -> float:
    """Distancia rectilínea entre dos puntos (x, y, etiqueta)."""
    xa, ya = a[0], a[1]
    xb, yb = b[0], b[1]
    if xa == xb:
        return abs(ya - yb)
    return ya + yb + abs(xa - xb)


def trazo(a: tuple, b: tuple) -> list[tuple]:
    """Camino real que sigue el surtidor entre dos puntos (para dibujar la ruta)."""
    if a[0] == b[0]:
        return [a, b]
    return [a, (a[0], 0.0), (b[0], 0.0), b]


def longitud(ruta: list[tuple]) -> float:
    return sum(dist(ruta[i], ruta[i + 1]) for i in range(len(ruta) - 1))


def ruta_vecino_mas_cercano(paradas: list[tuple]) -> list[tuple]:
    """Heurística constructiva: siempre ir a la parada no visitada más cercana."""
    pendientes = list(paradas)
    actual = ORIGEN
    ruta = [ORIGEN]
    while pendientes:
        siguiente = min(pendientes, key=lambda q: dist(actual, q))
        pendientes.remove(siguiente)
        ruta.append(siguiente)
        actual = siguiente
    ruta.append(ORIGEN)
    return ruta


def mejorar_2opt(ruta: list[tuple]) -> list[tuple]:
    """
    Mejora 2-opt: invierte segmentos mientras reduzcan la longitud de la ruta cerrada.
    La ruta empieza y termina en el almacén.
    """
    t = list(ruta)
    mejorado = True
    while mejorado:
        mejorado = False
        for i in range(1, len(t) - 2):
            for j in range(i + 1, len(t) - 1):
                a, b = t[i - 1], t[i]
                c, d = t[j], t[j + 1]
                delta = dist(a, c) + dist(b, d) - dist(a, b) - dist(c, d)
                if delta < -1e-9:
                    t[i:j + 1] = t[i:j + 1][::-1]
                    mejorado = True
    return t


# =====================================================================
# Datos
# =====================================================================
def _parametros() -> dict:
    with st.expander("⚙️ Ajustes de la tienda", expanded=False):
        c1, c2, c3, c4, c5 = st.columns(5)
        pasillos = c1.number_input("Pasillos de venta", min_value=1, max_value=20, value=8,
                                   key="lay_pasillos")
        largo = c2.number_input("Largo de pasillo (m)", min_value=8.0, max_value=60.0,
                                value=20.0, step=2.0, key="lay_largo")
        sep = c3.number_input("Separación entre pasillos (m)", min_value=2.0, max_value=10.0,
                              value=5.0, step=0.5, key="lay_sep")
        vel = c4.number_input("Velocidad de caminata (m/s)", min_value=0.5, max_value=2.0,
                              value=1.2, step=0.1, key="lay_vel")
        pick = c5.number_input("Min. por producto tomado", min_value=0.1, max_value=2.0,
                               value=0.3, step=0.1, key="lay_pick")
    return {"pasillos": int(pasillos), "largo": float(largo), "sep": float(sep),
            "vel": float(vel), "pick": float(pick)}


def _slots(P: dict) -> list[tuple[int, float]]:
    """Posiciones disponibles: un espacio cada 2 m a lo largo de cada pasillo."""
    return [(p, float(y)) for p in range(1, P["pasillos"] + 1)
            for y in np.arange(1, P["largo"] + 1, 2)]


def generar_demo_layout(P: dict, semilla: int | None = None) -> int:
    """Ubicación desordenada a propósito (el «antes»), con frecuencias tipo Pareto."""
    rng = np.random.default_rng(semilla)
    prods = db.query_df("SELECT sku FROM productos ORDER BY sku")
    if prods.empty:
        return 0
    slots = _slots(P)
    n = len(prods)
    if len(slots) < n:
        return 0
    rangos = rng.permutation(n) + 1
    frec = np.round(220 / rangos ** 0.9, 1)
    eleccion = rng.permutation(len(slots))[:n]
    filas = []
    for sku, k, f in zip(prods["sku"], eleccion, frec):
        p, y = slots[k]
        filas.append((sku, p, y, float(f)))
    db.execute("DELETE FROM ubicaciones_layout")
    db.executemany(
        "INSERT INTO ubicaciones_layout (sku, pasillo, posicion, frecuencia) VALUES (?, ?, ?, ?)",
        filas,
    )
    return len(filas)


def cargar(P: dict) -> pd.DataFrame:
    df = db.query_df(
        """SELECT u.sku, p.producto, p.departamento, u.pasillo, u.posicion, u.frecuencia
           FROM ubicaciones_layout u JOIN productos p ON p.sku = u.sku
           ORDER BY u.frecuencia DESC"""
    )
    if df.empty:
        return df
    df["x"] = df["pasillo"].map(lambda p: x_pasillo(int(p), P["sep"]))
    df["dist_m"] = df["x"] + df["posicion"]                # desde el almacén (ida)
    df["metros_dia"] = 2 * df["dist_m"] * df["frecuencia"]  # ida y vuelta por surtido
    total = df["frecuencia"].sum()
    previo = (df["frecuencia"].cumsum() - df["frecuencia"]) / total * 100 if total else 0
    df["clase"] = np.where(previo < 80, "A", np.where(previo < 95, "B", "C"))
    df["fuera_plano"] = (df["pasillo"] > P["pasillos"]) | (df["posicion"] > P["largo"])
    return df


def propuesta_por_rotacion(df: pd.DataFrame, P: dict) -> pd.DataFrame:
    """Coloca los productos de mayor frecuencia en los espacios más cercanos al almacén."""
    orden = df.sort_values("frecuencia", ascending=False).reset_index(drop=True)
    espacios = sorted(_slots(P), key=lambda s: x_pasillo(s[0], P["sep"]) + s[1])
    if len(espacios) < len(orden):
        return None  # no caben todos los productos con la configuración actual
    nuevo = orden.copy()
    for i in range(len(nuevo)):
        p, y = espacios[i]
        nuevo.loc[i, "pasillo"] = p
        nuevo.loc[i, "posicion"] = y
    nuevo["x"] = nuevo["pasillo"].map(lambda p: x_pasillo(int(p), P["sep"]))
    nuevo["dist_m"] = nuevo["x"] + nuevo["posicion"]
    nuevo["metros_dia"] = 2 * nuevo["dist_m"] * nuevo["frecuencia"]
    return nuevo


def _puntos_de(df: pd.DataFrame, skus: list[str]) -> list[tuple]:
    indice = df.set_index("sku")
    puntos = []
    for sku in skus:
        if sku in indice.index:
            r = indice.loc[sku]
            puntos.append((float(r["x"]), float(r["posicion"]), sku))
    return puntos


# =====================================================================
# Visualización
# =====================================================================
def _plano(df: pd.DataFrame, ruta: list[tuple] | None, P: dict, titulo: str) -> go.Figure:
    fig = go.Figure()
    xmax = x_pasillo(P["pasillos"], P["sep"])
    fig.add_trace(go.Scatter(x=[0, xmax], y=[0, 0], mode="lines",
                             line=dict(color="#90A4AE", width=12), hoverinfo="skip",
                             name="Pasillo principal"))
    for p in range(1, P["pasillos"] + 1):
        x = x_pasillo(p, P["sep"])
        fig.add_trace(go.Scatter(x=[x, x], y=[0, P["largo"]], mode="lines",
                                 line=dict(color="#CFD8DC", width=18), hoverinfo="skip",
                                 showlegend=False))
        fig.add_annotation(x=x, y=P["largo"] + 1.5, text=f"P{p}", showarrow=False,
                           font=dict(size=11, color="#546E7A"))

    if not df.empty:
        colores = df["clase"].map({"A": ui.COLOR_A, "B": ui.COLOR_B, "C": ui.COLOR_C})
        fig.add_trace(go.Scatter(
            x=df["x"], y=df["posicion"], mode="markers", name="Productos",
            marker=dict(color=colores, size=9, line=dict(color="white", width=1)),
            text=df["producto"] + " (" + df["sku"] + ")",
            hovertemplate="%{text}<br>%{x:.0f} m, %{y:.0f} m<extra></extra>",
        ))

    if ruta:
        xs, ys = [], []
        for i in range(len(ruta) - 1):
            for q in trazo(ruta[i], ruta[i + 1]):
                xs.append(q[0])
                ys.append(q[1])
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="Ruta de surtido",
                                 line=dict(color=ui.COLOR_LINEA, width=3)))
        paradas = ruta[1:-1]
        fig.add_trace(go.Scatter(
            x=[p[0] for p in paradas], y=[p[1] for p in paradas], mode="markers+text",
            text=[str(i + 1) for i in range(len(paradas))], textposition="top center",
            marker=dict(color=ui.COLOR_LINEA, size=14), name="Paradas (orden)",
            hovertext=[p[2] for p in paradas], hoverinfo="text",
        ))

    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", text=["Almacén"],
                             textposition="bottom right",
                             marker=dict(symbol="square", size=16, color="black"),
                             name="Almacén", hoverinfo="skip"))
    fig.update_layout(title=titulo, height=460, margin=dict(l=10, r=10, t=50, b=10),
                      xaxis_title="Metros (a lo largo del piso)", yaxis_title="Metros",
                      legend=dict(orientation="h", y=-0.22), plot_bgcolor="white")
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


# =====================================================================
# Pestañas
# =====================================================================
def _tab_plano(df: pd.DataFrame, P: dict) -> None:
    if df.empty:
        st.info("Aún no hay ubicaciones. Carga la demostración en la pestaña **Datos**.")
        return

    st.markdown("#### Lista de surtido")
    c1, c2 = st.columns([1, 2])
    tam = c1.slider("Productos en la lista", 6, 25, 14, key="lay_tam")
    if c2.button("🎲 Generar nueva lista de surtido"):
        rng = np.random.default_rng()
        p = df["frecuencia"] / df["frecuencia"].sum()
        elegidos = rng.choice(df["sku"].to_numpy(), size=min(tam, len(df)), replace=False,
                              p=p.to_numpy())
        st.session_state["lay_lista"] = list(elegidos)
    if "lay_lista" not in st.session_state:
        st.session_state["lay_lista"] = list(df["sku"].head(tam))
    lista = [s for s in st.session_state["lay_lista"] if s in set(df["sku"])][:tam]
    st.caption(f"Orden de captura del surtidor: {len(lista)} productos. "
               "La ruta actual sigue ese orden.")

    paradas = _puntos_de(df, lista)
    if not paradas:
        st.warning("Los productos de la lista no tienen ubicación.")
        return

    actual = [ORIGEN] + paradas + [ORIGEN]
    nn = ruta_vecino_mas_cercano(paradas)
    opt = mejorar_2opt(nn)
    rutas = {"Ruta actual": actual, "Vecino más cercano": nn, "2-opt (mejorada)": opt}
    largos = {k: longitud(v) for k, v in rutas.items()}
    base = largos["Ruta actual"]

    st.markdown("#### Ruta de surtido")
    metodo = st.radio("Ruta a mostrar", list(rutas), horizontal=True, key="lay_metodo")
    ruta = rutas[metodo]
    largo_sel = largos[metodo]
    minutos = largo_sel / P["vel"] / 60 + len(paradas) * P["pick"]
    ahorro = (base - largo_sel) / base * 100 if base else 0

    k = st.columns(4)
    k[0].metric("Distancia de la ruta", f"{largo_sel:.0f} m")
    k[1].metric("Tiempo estimado del surtido", f"{minutos:.1f} min",
                "incluye caminar y tomar productos", delta_color="off")
    k[2].metric("Ahorro vs. ruta actual", f"{ahorro:.0f}%",
                f"{base - largo_sel:.0f} m menos" if base > largo_sel else None,
                delta_color="off")
    k[3].metric("Paradas", len(paradas))

    st.plotly_chart(_plano(df, ruta, P, f"Recorrido: {metodo.lower()}"), key="lay_fig_plano")

    comp = pd.DataFrame({"Método": list(largos), "Metros": list(largos.values())})
    fig = px.bar(comp, x="Método", y="Metros", text=comp["Metros"].map(lambda v: f"{v:.0f} m"),
                 title="Comparación de métodos de ruta",
                 color="Método",
                 color_discrete_map={"Ruta actual": ui.COLOR_A,
                                     "Vecino más cercano": ui.COLOR_B,
                                     "2-opt (mejorada)": ui.COLOR_PRIMARIO})
    fig.update_layout(showlegend=False, height=330, margin=dict(l=10, r=10, t=50, b=10))
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, key="lay_fig_comp")

    ui.insight(
        f"🧭 Recorrer la lista en el orden actual cuesta <b>{base:.0f} m</b>. El vecino más "
        f"cercano lo baja a <b>{largos['Vecino más cercano']:.0f} m</b> y la mejora 2-opt a "
        f"<b>{largos['2-opt (mejorada)']:.0f} m</b>, un ahorro de "
        f"<b>{(base - largos['2-opt (mejorada)']) / base * 100:.0f}%</b> sin mover un solo producto."
    )
    with st.expander("Secuencia de paradas de la ruta mejorada"):
        seq = pd.DataFrame([{"Parada": i + 1, "SKU": q[2],
                             "Pasillo": f"P{int(round((q[0] - OFFSET_M) / P['sep'])) + 1}",
                             "Metros desde almacén": round(q[0] + q[1], 1)}
                            for i, q in enumerate(opt[1:-1])])
        st.dataframe(seq, hide_index=True)


def _tab_distancias(df: pd.DataFrame, P: dict) -> None:
    if df.empty:
        st.info("Sin ubicaciones. Carga la demostración en **Datos**.")
        return
    st.markdown("#### Distancia de cada pasillo al almacén")
    pas = pd.DataFrame([{
        "Pasillo": f"P{p}", "Entrada (m)": round(x_pasillo(p, P["sep"]), 1),
        "Fondo del pasillo (m)": round(x_pasillo(p, P["sep"]) + P["largo"], 1),
        "Productos": int((df["pasillo"] == p).sum()),
    } for p in range(1, P["pasillos"] + 1)])
    st.dataframe(pas, hide_index=True, use_container_width=True)

    st.markdown("#### Distancia de cada producto al almacén")
    d = df.sort_values("dist_m")
    fig = px.bar(d, x="dist_m", y="producto", color="clase", orientation="h",
                 color_discrete_map={"A": ui.COLOR_A, "B": ui.COLOR_B, "C": ui.COLOR_C},
                 labels={"dist_m": "Metros desde el almacén (ida)", "producto": "",
                         "clase": "Clase por frecuencia"},
                 title="Ubicación actual: productos más lejanos abajo")
    fig.update_layout(height=max(420, 22 * len(d)), margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=1.06))
    st.plotly_chart(fig, key="lay_fig_dist")

    lejos_a = df[(df["clase"] == "A") & (df["dist_m"] > df["dist_m"].median())]
    if len(lejos_a):
        ui.insight(f"🔎 <b>{len(lejos_a)}</b> productos de clase A (los que más se surten) están "
                   "por encima de la mediana de distancia. Son los primeros a reubicar.")


def _tab_rotacion(df: pd.DataFrame, P: dict) -> None:
    if df.empty:
        st.info("Sin ubicaciones. Carga la demostración en **Datos**.")
        return
    prop = propuesta_por_rotacion(df, P)
    st.markdown("#### Reubicación por rotación (ABC de frecuencia)")
    if prop is None:
        st.warning("No caben todos los productos con la configuración actual. Aumenta los "
                   "pasillos o el largo en los parámetros.")
        return
    actual_m = df["metros_dia"].sum()
    prop_m = prop["metros_dia"].sum()
    ahorro_m = actual_m - prop_m
    ahorro_min = ahorro_m / P["vel"] / 60

    st.caption("Los productos de mayor frecuencia de surtido se mueven a los espacios más "
               "cercanos al almacén. Métrica: metros diarios de ida y vuelta por surtido.")
    base = df.set_index("sku")[["pasillo", "posicion"]]
    nueva = prop.set_index("sku")[["pasillo", "posicion"]]
    cambian = int((base.loc[nueva.index] != nueva).any(axis=1).sum())
    k = st.columns(4)
    k[0].metric("Metros/día ubicación actual", f"{actual_m:,.0f} m")
    k[1].metric("Metros/día con propuesta", f"{prop_m:,.0f} m")
    k[2].metric("Ahorro diario", f"{ahorro_m / max(actual_m, 1) * 100:.0f}%",
                f"{ahorro_m:,.0f} m · {ahorro_min:.0f} min", delta_color="off")
    k[3].metric("Productos que cambian", cambian)

    ui.insight(f"🔁 Reubicar por rotación ahorra <b>{ahorro_m:,.0f} m al día</b> "
               f"(≈ <b>{ahorro_min:.0f} min</b> de caminata de surtidores), sin cambiar pasillos "
               "ni equipo. El cambio se hace una sola vez y después se mantiene con FEFO.")

    tabla = prop[["sku", "producto", "clase", "frecuencia", "metros_dia"]].copy()
    tabla["Actual"] = df.set_index("sku").loc[tabla["sku"], "pasillo"].map(lambda p: f"P{int(p)}").values
    tabla["Propuesta"] = prop["pasillo"].map(lambda p: f"P{int(p)}").values
    tabla["Posición propuesta (m)"] = prop["posicion"].round(1).values
    st.dataframe(
        tabla.rename(columns={"sku": "SKU", "producto": "Producto", "clase": "Clase",
                              "frecuencia": "Surtidos/día", "metros_dia": "Metros/día"}),
        hide_index=True, height=380,
        column_config={
            "Metros/día": st.column_config.NumberColumn(format="%.0f m"),
            "Surtidos/día": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    if st.button("✅ Aplicar la propuesta como nueva ubicación", type="primary"):
        filas = [(r["sku"], int(r["pasillo"]), float(r["posicion"]), float(r["frecuencia"]))
                 for _, r in prop.iterrows()]
        db.execute("DELETE FROM ubicaciones_layout")
        db.executemany("INSERT INTO ubicaciones_layout (sku, pasillo, posicion, frecuencia) "
                       "VALUES (?, ?, ?, ?)", filas)
        st.session_state["lay_flash"] = "Propuesta aplicada: las ubicaciones ya son las nuevas."
        st.rerun()


def _tab_operaciones(df: pd.DataFrame, P: dict) -> None:
    st.markdown("#### Diagrama de operaciones y recorrido (ASME)")
    st.caption("Tiempos del surtido de un pedido. Ajusta los tiempos de cada paso según tu "
               "medición con cronómetro.")
    c1, c2, c3 = st.columns(3)
    recibir = c1.number_input("Recibir y revisar la lista (min)", 0.0, 10.0, 0.5, 0.25,
                              key="ops_recibir")
    inspec = c2.number_input("Verificar por producto (min)", 0.0, 2.0, 0.2, 0.05,
                             key="ops_inspec")
    espera = c3.number_input("Esperar disponibilidad de cajón o montacargas (min)", 0.0, 30.0,
                             2.0, 0.5, key="ops_espera")
    c4, c5, c6 = st.columns(3)
    empacar = c4.number_input("Empacar el pedido (min)", 0.0, 30.0, 1.5, 0.5, key="ops_empacar")
    llevar = c5.number_input("Llevar a zona de entrega (min)", 0.0, 30.0, 3.0, 0.5,
                             key="ops_llevar")
    entregar = c6.number_input("Entregar o acomodar (min)", 0.0, 30.0, 0.5, 0.5,
                               key="ops_entregar")

    if df.empty or "lay_lista" not in st.session_state:
        st.info("Genera una lista de surtido en la pestaña **Plano y ruta** para calcular "
                "el diagrama con una ruta real.")
        return
    lista = [s for s in st.session_state["lay_lista"] if s in set(df["sku"])]
    paradas = _puntos_de(df, lista)
    if not paradas:
        return
    ruta = mejorar_2opt(ruta_vecino_mas_cercano(paradas))
    n = len(paradas)
    minutos_transporte = longitud(ruta) / P["vel"] / 60
    pasos = [
        ("Operación", "Recibir y revisar la lista de surtido", recibir),
        ("Transporte", f"Recorrer el piso ({longitud(ruta):.0f} m, ruta 2-opt)",
         minutos_transporte),
        ("Operación", f"Tomar {n} productos", n * P["pick"]),
        ("Inspección", "Verificar cantidad y caducidad", n * inspec),
        ("Demora", "Esperar cajón o montacargas", espera),
        ("Operación", "Empacar el pedido", empacar),
        ("Transporte", "Llevar el pedido a la zona de entrega", llevar),
        ("Operación", "Entregar o acomodar", entregar),
    ]
    diag = pd.DataFrame(pasos, columns=["Tipo", "Paso", "Minutos"])
    diag.insert(0, "Símbolo", diag["Tipo"].map(SIMBOLOS))
    diag.insert(0, "#", range(1, len(diag) + 1))
    total = diag["Minutos"].sum()
    desperdicio = diag.loc[diag["Tipo"].isin(["Transporte", "Demora"]), "Minutos"].sum()

    k = st.columns(3)
    k[0].metric("Tiempo total del surtido", f"{total:.1f} min")
    k[1].metric("Transporte y demora", f"{desperdicio / total * 100:.0f}%",
                "tiempo que no agrega valor", delta_color="inverse")
    k[2].metric("Pedidos por hora (un surtidor)", f"{60 / total:.1f}")

    st.dataframe(diag, hide_index=True, column_config={
        "Minutos": st.column_config.NumberColumn(format="%.1f")})
    por_tipo = diag.groupby("Tipo", as_index=False)["Minutos"].sum()
    fig = px.bar(por_tipo, x="Minutos", y="Tipo", orientation="h", color="Tipo",
                 color_discrete_map={"Operación": ui.COLOR_PRIMARIO, "Transporte": ui.COLOR_LINEA,
                                     "Inspección": ui.COLOR_B, "Demora": ui.COLOR_A},
                 title="Minutos por tipo de operación")
    fig.update_layout(showlegend=False, height=300, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, key="lay_fig_ops")

    ui.insight(f"🧭 El {desperdicio / total * 100:.0f}% del tiempo del surtido es transporte o "
               "demora. Reducir la distancia (ruta y reubicación) y las esperas es la vía más "
               "directa para mejorar la productividad sin contratar personal.")


def _tab_datos(df: pd.DataFrame, P: dict) -> None:
    if "lay_flash" in st.session_state:
        st.success(st.session_state.pop("lay_flash"))
    st.markdown("#### Ubicaciones actuales")
    st.caption("Puedes editar pasillo y posición directamente. Guarda para aplicar.")
    if df.empty:
        st.info("No hay ubicaciones registradas.")
    else:
        fuera = int(df["fuera_plano"].sum())
        if fuera:
            st.warning(f"{fuera} producto(s) quedan fuera del plano actual. Cambia el número de "
                       "pasillos o el largo, o aplica una reubicación.")
        editado = st.data_editor(
            df[["sku", "producto", "pasillo", "posicion", "frecuencia"]],
            hide_index=True, key="lay_editor", height=380,
            disabled=["sku", "producto", "frecuencia"],
            column_config={
                "pasillo": st.column_config.NumberColumn("Pasillo", min_value=1,
                                                         max_value=P["pasillos"], step=1),
                "posicion": st.column_config.NumberColumn("Posición (m)", min_value=0.0,
                                                          max_value=P["largo"], step=0.5),
                "frecuencia": st.column_config.NumberColumn("Surtidos/día", format="%.1f"),
            },
        )
        cambios = editado[(editado["pasillo"] != df["pasillo"].values) |
                          (editado["posicion"] != df["posicion"].values)]
        if len(cambios) and st.button(f"Guardar {len(cambios)} cambio(s) de ubicación",
                                      type="primary"):
            for _, r in cambios.iterrows():
                db.execute("UPDATE ubicaciones_layout SET pasillo = ?, posicion = ? WHERE sku = ?",
                           (int(r["pasillo"]), float(r["posicion"]), r["sku"]))
            st.session_state["lay_flash"] = f"Se guardaron {len(cambios)} cambio(s)."
            st.rerun()

    st.markdown("#### Administración")
    a1, a2 = st.columns(2)
    if a1.button("🎲 Generar ubicación de demostración (desordenada)"):
        n = generar_demo_layout(P)
        st.session_state["lay_flash"] = (f"Se generaron {n} ubicaciones." if n else
                                         "No hay espacio suficiente: sube pasillos o largo.")
        st.rerun()
    confirmar = a2.checkbox("Confirmo borrar las ubicaciones", key="lay_conf")
    if a2.button("Borrar ubicaciones", disabled=not confirmar):
        db.execute("DELETE FROM ubicaciones_layout")
        st.session_state["lay_flash"] = "Ubicaciones borradas."
        st.rerun()


# =====================================================================
# Punto de entrada
# =====================================================================
def render() -> None:
    ui.page_header(
        "Optimización de Layout y Recorridos",
        "Distancia rectilínea · ruta de surtido (vecino más cercano y 2-opt) · "
        "reubicación por rotación · diagrama de operaciones",
        "🗺️",
    )
    P = _parametros()
    df = cargar(P)
    t1, t2, t3, t4, t5 = st.tabs(["🧭 Plano y ruta", "📏 Distancias", "🔁 Rotación (ABC)",
                                  "⚙️ Operaciones", "🗂️ Datos"])
    with t1:
        _tab_plano(df, P)
    with t2:
        _tab_distancias(df, P)
    with t3:
        _tab_rotacion(df, P)
    with t4:
        _tab_operaciones(df, P)
    with t5:
        _tab_datos(df, P)
