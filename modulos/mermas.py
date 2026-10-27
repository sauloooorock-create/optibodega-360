"""
Módulo 2 · Análisis de Mermas y Costos (Diagrama de Pareto, Ley 80/20)

Flujo de mejora continua que implementa:
    1. Registro      -> captura individual o carga masiva (CSV/Excel) de mermas.
    2. Pareto        -> identifica los "pocos vitales" (clase A) por producto,
                        departamento, categoría, causa o turno; estratificación
                        de segundo nivel y estimación de ahorro potencial.
    3. Análisis      -> tendencia, mapa de calor, gráfica de control (X ± 3σ),
                        patrones por turno/día y mapa de árbol.
    4. Plan de acción-> acciones correctivas (PHVA) ligadas a los focos clase A.
    5. Datos         -> consulta, exportación a Excel/CSV y administración.
"""

from __future__ import annotations

import io
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from modulos import database as db
from modulos import ui
from modulos.catalogos import (
    CATEGORIAS_MERMA,
    CAUSAS_POR_CATEGORIA,
    ESTADOS_ACCION,
    HERRAMIENTAS_MEJORA,
    TURNOS,
    UNIDADES,
)

# Etiqueta visible -> columna de la tabla `mermas`
DIMENSIONES = {
    "Producto": "producto",
    "Departamento": "departamento",
    "Categoría de merma": "categoria",
    "Causa raíz": "causa",
    "Turno": "turno",
}

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

COLUMNAS_PLANTILLA = [
    "fecha", "turno", "departamento", "sku", "producto", "categoria",
    "causa", "cantidad", "unidad", "costo_unitario", "responsable", "observaciones",
]

_SQL_INSERT = """
INSERT INTO mermas (fecha, turno, departamento, sku, producto, categoria, causa,
                    cantidad, unidad, costo_unitario, costo_total, responsable,
                    observaciones, origen)
VALUES (:fecha, :turno, :departamento, :sku, :producto, :categoria, :causa,
        :cantidad, :unidad, :costo_unitario, :costo_total, :responsable,
        :observaciones, :origen)
"""


# =====================================================================
# Capa de datos
# =====================================================================
def obtener_mermas() -> pd.DataFrame:
    df = db.query_df("SELECT * FROM mermas ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["causa"] = df["causa"].fillna("Sin especificar")
        df["turno"] = df["turno"].fillna("Sin especificar")
    return df


def obtener_productos() -> pd.DataFrame:
    return db.query_df("SELECT * FROM productos ORDER BY departamento, producto")


def obtener_acciones() -> pd.DataFrame:
    return db.query_df("SELECT * FROM acciones_mermas ORDER BY id DESC")


def registrar_merma(registro: dict) -> int:
    registro = dict(registro)
    registro["costo_total"] = round(registro["cantidad"] * registro["costo_unitario"], 2)
    registro.setdefault("origen", "manual")
    return db.execute(_SQL_INSERT, registro)


def insertar_lote(df: pd.DataFrame, origen: str) -> int:
    df = df.copy()
    df["costo_total"] = (df["cantidad"] * df["costo_unitario"]).round(2)
    df["origen"] = origen
    filas = df[COLUMNAS_PLANTILLA + ["costo_total", "origen"]].to_dict("records")
    db.executemany(_SQL_INSERT, filas)
    return len(filas)


def generar_datos_demo(n: int = 650, dias: int = 90, semilla: int | None = None) -> int:
    """Genera mermas sintéticas con una distribución tipo Pareto realista."""
    rng = np.random.default_rng(semilla)
    prods = obtener_productos()
    if prods.empty:
        return 0

    pesos_depto = {
        "Frutas y Verduras": 0.34, "Carnes y Pescados": 0.24,
        "Lácteos y Refrigerados": 0.14, "Panadería y Tortillería": 0.10,
        "Salchichonería": 0.06, "Abarrotes": 0.05, "Bebidas": 0.03,
        "Limpieza y Hogar": 0.02, "Mercancías Generales": 0.02,
    }
    # Probabilidad por categoría, en el orden de CATEGORIAS_MERMA:
    # Caducidad, Daño, Manejo, Faltante, Calidad de proveedor
    perfil_perecedero = [0.55, 0.12, 0.20, 0.04, 0.09]
    perfil_seco = [0.06, 0.40, 0.34, 0.15, 0.05]
    perfil_general = [0.00, 0.35, 0.20, 0.45, 0.00]
    perecederos = {"Frutas y Verduras", "Carnes y Pescados", "Lácteos y Refrigerados",
                   "Panadería y Tortillería", "Salchichonería"}

    deptos = prods["departamento"].unique().tolist()
    p_dep = np.array([pesos_depto.get(d, 0.03) for d in deptos])
    p_dep = p_dep / p_dep.sum()

    # Pesos tipo Zipf dentro de cada departamento: pocos productos dominan
    pesos_prod = {}
    for d in deptos:
        idx = rng.permutation(prods.index[prods["departamento"] == d].to_numpy())
        w = 1 / np.arange(1, len(idx) + 1) ** 1.9
        pesos_prod[d] = (idx, w / w.sum())

    responsables = ["Jefe de piso", "Encargado de perecederos", "Recibo",
                    "Gerente de turno", "Auxiliar de almacén"]
    hoy = date.today()
    filas = []
    for _ in range(n):
        d = rng.choice(deptos, p=p_dep)
        idx, w = pesos_prod[d]
        prod = prods.loc[rng.choice(idx, p=w)]
        if d in perecederos:
            perfil = perfil_perecedero
        elif d == "Mercancías Generales":
            perfil = perfil_general
        else:
            perfil = perfil_seco
        cat = rng.choice(CATEGORIAS_MERMA, p=perfil)
        causas = CAUSAS_POR_CATEGORIA[cat]
        wc = np.linspace(2, 1, len(causas))
        causa = rng.choice(causas, p=wc / wc.sum())

        if prod["unidad"] == "kg":
            cantidad = max(0.1, round(float(rng.gamma(2.0, 1.8)), 2))
        elif prod["costo_unitario"] > 100:
            cantidad = float(rng.integers(1, 4))
        else:
            cantidad = float(rng.poisson(6) + 1)

        costo_u = round(float(prod["costo_unitario"]) * rng.uniform(0.97, 1.03), 2)
        fecha = hoy - timedelta(days=int(rng.integers(0, dias)))
        filas.append({
            "fecha": fecha.isoformat(),
            "turno": rng.choice(TURNOS, p=[0.45, 0.40, 0.15]),
            "departamento": d,
            "sku": prod["sku"],
            "producto": prod["producto"],
            "categoria": cat,
            "causa": causa,
            "cantidad": cantidad,
            "unidad": prod["unidad"],
            "costo_unitario": costo_u,
            "costo_total": round(cantidad * costo_u, 2),
            "responsable": rng.choice(responsables),
            "observaciones": "",
            "origen": "demo",
        })
    db.executemany(_SQL_INSERT, filas)
    return len(filas)


# =====================================================================
# Lógica de ingeniería: Pareto / ABC
# =====================================================================
def calcular_pareto(df: pd.DataFrame, columna: str, metrica: str = "costo",
                    umbral_a: float = 80, umbral_b: float = 95) -> pd.DataFrame:
    """
    Tabla de Pareto con clasificación ABC.

    Un elemento es clase A si el acumulado *antes* de sumarlo es < umbral_a;
    así el elemento que cruza el 80 % queda dentro de los pocos vitales.
    """
    if df.empty:
        return pd.DataFrame(columns=["rank", columna, "costo", "eventos", "cantidad",
                                     "pct", "pct_acum", "clase"])
    agg = (
        df.groupby(columna, as_index=False)
        .agg(costo=("costo_total", "sum"), eventos=("id", "count"), cantidad=("cantidad", "sum"))
    )
    valor = "costo" if metrica == "costo" else "eventos"
    agg = agg.sort_values(valor, ascending=False).reset_index(drop=True)
    total = agg[valor].sum()
    agg["pct"] = agg[valor] / total * 100 if total else 0
    agg["pct_acum"] = agg["pct"].cumsum()
    previo = agg["pct_acum"] - agg["pct"]
    agg["clase"] = np.where(previo < umbral_a, "A", np.where(previo < umbral_b, "B", "C"))
    agg.insert(0, "rank", range(1, len(agg) + 1))
    return agg


def grafica_pareto(par: pd.DataFrame, columna: str, metrica: str = "costo",
                   top_n: int = 15, umbral: float = 80, titulo: str = "") -> go.Figure:
    valor = "costo" if metrica == "costo" else "eventos"
    d = par[[columna, valor, "pct", "pct_acum", "clase"]].copy()
    if len(d) > top_n:
        resto = d.iloc[top_n:]
        otros = pd.DataFrame([{
            columna: f"Otros ({len(resto)})", valor: resto[valor].sum(),
            "pct": resto["pct"].sum(), "pct_acum": 100.0, "clase": "Otros",
        }])
        d = pd.concat([d.iloc[:top_n], otros], ignore_index=True)

    colores = d["clase"].map({"A": ui.COLOR_A, "B": ui.COLOR_B, "C": ui.COLOR_C,
                              "Otros": "#BDBDBD"})
    x = d[columna].astype(str).tolist()
    if valor == "costo":
        texto = [ui.money(v) for v in d[valor]]
        eje_y = "Pérdida (MXN)"
    else:
        texto = [f"{int(v)}" for v in d[valor]]
        eje_y = "Eventos"

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=x, y=d[valor], marker_color=colores, text=texto, textposition="outside",
            cliponaxis=False, name=eje_y,
            customdata=list(zip(d["pct"].round(1), d["clase"])),
            hovertemplate="<b>%{x}</b><br>" + eje_y + ": %{text}"
                          "<br>Participación: %{customdata[0]}%"
                          "<br>Clase: %{customdata[1]}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=d["pct_acum"], mode="lines+markers", name="% acumulado",
            line=dict(color=ui.COLOR_LINEA, width=2.5), marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>Acumulado: %{y:.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_shape(type="line", xref="paper", x0=0, x1=1, yref="y2", y0=umbral, y1=umbral,
                  line=dict(color=ui.COLOR_A, dash="dash", width=1.5))
    fig.add_annotation(xref="paper", x=1, yref="y2", y=umbral, text=f"{umbral:.0f}%",
                       showarrow=False, xanchor="right", yanchor="bottom",
                       font=dict(color=ui.COLOR_A))
    fig.update_layout(
        title=titulo, height=500, bargap=0.18,
        margin=dict(l=10, r=10, t=60 if titulo else 30, b=10),
        legend=dict(orientation="h", y=1.08, x=0),
        hovermode="x unified" if len(d) > 25 else "closest",
    )
    fig.update_xaxes(tickangle=-35)
    fig.update_yaxes(title_text=eje_y, secondary_y=False, range=[0, d[valor].max() * 1.18])
    fig.update_yaxes(title_text="% acumulado", secondary_y=True, range=[0, 105],
                     ticksuffix="%", showgrid=False)
    return fig


def _texto_insight(par: pd.DataFrame, etiqueta: str, metrica: str) -> str:
    n = len(par)
    a = par[par["clase"] == "A"]
    n_a = len(a)
    pct_elem = n_a / n * 100 if n else 0
    pct_val = a["pct"].sum()
    que = "de las pérdidas económicas" if metrica == "costo" else "de los eventos de merma"
    lista = ", ".join(f"<b>{v}</b>" for v in a.iloc[:, 1].astype(str).head(6))
    if n_a > 6:
        lista += f" y {n_a - 6} más"
    if pct_elem <= 35:
        lectura = ("Se cumple el principio de Pareto: concentra los recursos de mejora "
                   "en estos elementos para obtener el mayor impacto.")
    else:
        lectura = ("La distribución es relativamente uniforme (no hay pocos vitales claros); "
                   "conviene estratificar con otra dimensión o con el Pareto de segundo nivel.")
    return (f"🔎 <b>{n_a} de {n}</b> {etiqueta.lower()}s ({pct_elem:.0f}% de los elementos) "
            f"concentran el <b>{pct_val:.1f}%</b> {que}.<br>Pocos vitales (clase A): {lista}."
            f"<br><span style='opacity:.8'>{lectura}</span>")


# =====================================================================
# Utilidades de interfaz
# =====================================================================
def _flash(msg: str, tipo: str = "success") -> None:
    st.session_state["mer_flash"] = (tipo, msg)


def _mostrar_flash() -> None:
    if "mer_flash" in st.session_state:
        tipo, msg = st.session_state.pop("mer_flash")
        getattr(st, tipo)(msg)


def _excel_bytes(hojas: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nombre, df in hojas.items():
            df.to_excel(writer, sheet_name=nombre[:31], index=False)
            hoja = writer.sheets[nombre[:31]]
            for col in hoja.columns:
                ancho = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                hoja.column_dimensions[col[0].column_letter].width = min(max(10, ancho + 2), 45)
    return buffer.getvalue()


def _filtros(df_all: pd.DataFrame) -> dict:
    min_d = df_all["fecha"].min().date()
    max_d = max(df_all["fecha"].max().date(), date.today())
    with st.expander("⚙️ Filtros", expanded=False):
        c1, c2, c3 = st.columns([1.2, 1.4, 1.4])
        rango = c1.date_input("Periodo", value=(min_d, max_d), key="mer_rango",
                              format="DD/MM/YYYY")
        deptos = c2.multiselect("Departamentos", sorted(df_all["departamento"].unique()),
                                key="mer_deptos", placeholder="Todos")
        cats = c3.multiselect("Categorías de merma", sorted(df_all["categoria"].unique()),
                              key="mer_cats", placeholder="Todas")
        c4, c5, _ = st.columns([1.2, 1.4, 1.4])
        venta = c4.number_input("Venta neta del periodo (MXN)", min_value=0.0, step=10000.0,
                                key="mer_venta",
                                help="Opcional. Permite calcular la merma como % de la venta.")
        meta = c5.number_input("Meta de merma (% de la venta)", min_value=0.0, max_value=20.0,
                               value=1.5, step=0.1, key="mer_meta")
    if isinstance(rango, (list, tuple)):
        ini, fin = (rango[0], rango[-1]) if len(rango) else (min_d, max_d)
    else:
        ini = fin = rango
    return {"ini": ini, "fin": fin, "deptos": deptos, "cats": cats, "venta": venta, "meta": meta}


def _aplicar(df: pd.DataFrame, f: dict, ini: date | None = None, fin: date | None = None):
    ini = ini or f["ini"]
    fin = fin or f["fin"]
    m = (df["fecha"].dt.date >= ini) & (df["fecha"].dt.date <= fin)
    if f["deptos"]:
        m &= df["departamento"].isin(f["deptos"])
    if f["cats"]:
        m &= df["categoria"].isin(f["cats"])
    return df[m]


def _kpis(df: pd.DataFrame, df_all: pd.DataFrame, f: dict) -> None:
    dias = (f["fin"] - f["ini"]).days + 1
    prev = _aplicar(df_all, f, f["ini"] - timedelta(days=dias), f["ini"] - timedelta(days=1))
    total, total_prev = df["costo_total"].sum(), prev["costo_total"].sum()
    eventos, eventos_prev = len(df), len(prev)

    def delta(a, b):
        return f"{(a - b) / b * 100:+.1f}% vs periodo anterior" if b else None

    c = st.columns(5)
    c[0].metric("Pérdida total", ui.money(total), delta(total, total_prev), delta_color="inverse")
    c[1].metric("Eventos de merma", f"{eventos:,}", delta(eventos, eventos_prev),
                delta_color="inverse")
    c[2].metric("Pérdida diaria promedio", ui.money(total / dias if dias else 0))
    if not df.empty:
        dep = df.groupby("departamento")["costo_total"].sum().sort_values(ascending=False)
        c[3].metric("Departamento crítico", dep.index[0],
                    f"{dep.iloc[0] / total * 100:.0f}% de la pérdida", delta_color="off")
    else:
        c[3].metric("Departamento crítico", "—")
    if f["venta"] > 0:
        pct = total / f["venta"] * 100
        c[4].metric("Merma / venta", f"{pct:.2f}%", f"{pct - f['meta']:+.2f} pp vs meta",
                    delta_color="inverse")
    else:
        c[4].metric("Merma / venta", "—", "Captura la venta en Filtros", delta_color="off")


def _sin_datos() -> None:
    st.info("No hay registros para los filtros seleccionados.")


# =====================================================================
# Pestañas
# =====================================================================
def _tab_registro(productos: pd.DataFrame) -> None:
    st.markdown("#### Registrar evento de merma")
    c1, c2, c3 = st.columns(3)
    deptos = productos["departamento"].unique().tolist()
    depto = c1.selectbox("Departamento", deptos, key="reg_depto")
    pd_dep = productos[productos["departamento"] == depto].set_index("sku")
    opciones = pd_dep.index.tolist() + ["__otro__"]
    sku = c2.selectbox(
        "Producto", opciones, key="reg_sku",
        format_func=lambda s: "➕ Otro (no catalogado)" if s == "__otro__"
        else f"{s} · {pd_dep.loc[s, 'producto']}",
    )
    categoria = c3.selectbox("Categoría de merma", CATEGORIAS_MERMA, key="reg_cat")

    with st.form("form_merma", clear_on_submit=True):
        nuevo_nombre = nuevo_sku = ""
        if sku == "__otro__":
            a, b, c = st.columns(3)
            nuevo_nombre = a.text_input("Nombre del producto *")
            nuevo_sku = b.text_input("SKU (opcional)")
            unidad = c.selectbox("Unidad", UNIDADES)
            costo_def = 0.0
        else:
            unidad = pd_dep.loc[sku, "unidad"]
            costo_def = float(pd_dep.loc[sku, "costo_unitario"])

        f1, f2, f3, f4 = st.columns(4)
        fecha = f1.date_input("Fecha", value=date.today(), max_value=date.today(),
                              format="DD/MM/YYYY")
        turno = f2.selectbox("Turno", TURNOS)
        cantidad = f3.number_input(f"Cantidad ({unidad}) *", min_value=0.0, step=1.0,
                                   format="%.2f")
        costo_u = f4.number_input("Costo unitario (MXN)", min_value=0.0, value=costo_def,
                                  step=0.5, format="%.2f")
        g1, g2 = st.columns(2)
        causa = g1.selectbox("Causa raíz", CAUSAS_POR_CATEGORIA[categoria] + ["Otra"])
        responsable = g2.text_input("Responsable / quien reporta")
        obs = st.text_area("Observaciones", height=70,
                           placeholder="Ej. Lote 2310 llegó con 2 días de vida útil.")
        enviado = st.form_submit_button("💾 Guardar merma", type="primary")

    if enviado:
        if cantidad <= 0:
            st.error("La cantidad debe ser mayor que cero.")
            return
        if sku == "__otro__" and not nuevo_nombre.strip():
            st.error("Escribe el nombre del producto no catalogado.")
            return
        if sku == "__otro__":
            nombre = nuevo_nombre.strip()
            sku_final = nuevo_sku.strip() or f"NC-{datetime.now():%y%m%d%H%M%S}"
            db.execute(
                """INSERT OR IGNORE INTO productos (sku, producto, departamento, unidad, costo_unitario)
                   VALUES (?, ?, ?, ?, ?)""",
                (sku_final, nombre, depto, unidad, costo_u),
            )
        else:
            nombre, sku_final = pd_dep.loc[sku, "producto"], sku
        registrar_merma({
            "fecha": fecha.isoformat(), "turno": turno, "departamento": depto,
            "sku": sku_final, "producto": nombre, "categoria": categoria, "causa": causa,
            "cantidad": float(cantidad), "unidad": unidad, "costo_unitario": float(costo_u),
            "responsable": responsable.strip(), "observaciones": obs.strip(),
        })
        _flash(f"Merma registrada: {cantidad:g} {unidad} de {nombre} · "
               f"pérdida de {ui.money(cantidad * costo_u, 2)}")
        st.rerun()

    with st.expander("📥 Carga masiva desde CSV o Excel"):
        st.caption("Descarga la plantilla, llénala con tus registros y súbela. "
                   "Campos obligatorios: fecha, departamento, producto, categoria, "
                   "cantidad, costo_unitario.")
        ejemplo = pd.DataFrame([{
            "fecha": date.today().isoformat(), "turno": TURNOS[0],
            "departamento": "Frutas y Verduras", "sku": "FV001", "producto": "Plátano Tabasco",
            "categoria": "Caducidad", "causa": "Sobreinventario / pedido excesivo",
            "cantidad": 4.5, "unidad": "kg", "costo_unitario": 14.5,
            "responsable": "Jefe de piso", "observaciones": "",
        }])
        st.download_button("⬇️ Plantilla CSV", ejemplo.to_csv(index=False).encode("utf-8-sig"),
                           "plantilla_mermas.csv", "text/csv")
        clave_upl = f"mer_upload_{st.session_state.get('mer_upl_n', 0)}"
        archivo = st.file_uploader("Archivo", type=["csv", "xlsx"], key=clave_upl)
        if archivo is not None:
            try:
                carga = (pd.read_csv(archivo) if archivo.name.endswith(".csv")
                         else pd.read_excel(archivo))
                carga.columns = [c.strip().lower() for c in carga.columns]
                obligatorias = ["fecha", "departamento", "producto", "categoria",
                                "cantidad", "costo_unitario"]
                faltan = [c for c in obligatorias if c not in carga.columns]
                if faltan:
                    st.error(f"Faltan columnas obligatorias: {', '.join(faltan)}")
                    return
                for c in COLUMNAS_PLANTILLA:
                    if c not in carga.columns:
                        carga[c] = ""
                carga["fecha"] = pd.to_datetime(carga["fecha"], dayfirst=False,
                                                errors="coerce").dt.date.astype(str)
                carga["cantidad"] = pd.to_numeric(carga["cantidad"], errors="coerce")
                carga["costo_unitario"] = pd.to_numeric(carga["costo_unitario"], errors="coerce")
                validas = carga.dropna(subset=["cantidad", "costo_unitario"])
                validas = validas[(validas["cantidad"] > 0) & (validas["fecha"] != "NaT")]
                carga = carga.fillna("")
                validas = validas.fillna("")
                st.write(f"Filas válidas: **{len(validas)}** de {len(carga)}")
                st.dataframe(validas.head(20), hide_index=True)
                if len(validas) and st.button(f"Importar {len(validas)} registros",
                                              type="primary"):
                    n = insertar_lote(validas, "carga_masiva")
                    # Cambiar la clave reinicia el cargador y evita importar dos veces
                    st.session_state["mer_upl_n"] = st.session_state.get("mer_upl_n", 0) + 1
                    _flash(f"Se importaron {n} registros de merma.")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo leer el archivo: {exc}")


def _tab_pareto(df: pd.DataFrame) -> None:
    if df.empty:
        return _sin_datos()

    c0, c1 = st.columns([2.2, 1])
    dim = c0.radio("Analizar por", list(DIMENSIONES), horizontal=True, key="par_dim")
    metrica_lbl = c1.radio("Métrica", ["Costo (MXN)", "Frecuencia"], horizontal=True,
                           key="par_met")
    metrica = "costo" if metrica_lbl.startswith("Costo") else "eventos"
    col = DIMENSIONES[dim]
    c2, c3 = st.columns(2)
    top_n = c2.slider("Barras a mostrar (el resto se agrupa en «Otros»)", 5, 30, 15,
                      key="par_top")
    umbral = c3.slider("Umbral de la clase A (%)", 60, 90, 80, step=5, key="par_umbral")

    par = calcular_pareto(df, col, metrica, umbral_a=umbral)
    st.plotly_chart(
        grafica_pareto(par, col, metrica, top_n, umbral,
                       f"Diagrama de Pareto de mermas por {dim.lower()}"),
        key="fig_pareto",
    )
    ui.insight(_texto_insight(par, dim, metrica))

    with st.expander("📋 Tabla de Pareto y clasificación ABC", expanded=False):
        st.dataframe(
            par.rename(columns={col: dim}),
            hide_index=True,
            column_config={
                "rank": st.column_config.NumberColumn("#", width="small"),
                "costo": st.column_config.NumberColumn("Pérdida (MXN)", format="$%.2f"),
                "eventos": st.column_config.NumberColumn("Eventos"),
                "cantidad": st.column_config.NumberColumn("Cantidad", format="%.2f"),
                "pct": st.column_config.NumberColumn("% del total", format="%.1f%%"),
                "pct_acum": st.column_config.ProgressColumn(
                    "% acumulado", format="%.1f%%", min_value=0, max_value=100),
                "clase": st.column_config.TextColumn("Clase ABC"),
            },
        )

    # ---- Estratificación de segundo nivel ---------------------------------
    st.markdown("#### 🔬 Pareto de segundo nivel (estratificación)")
    sub_col, sub_lbl = ("causa", "Causa raíz") if col == "producto" else ("producto", "Producto")
    s1, s2 = st.columns([1.3, 2])
    foco = s1.selectbox(f"Desglosar {dim.lower()}", par[col].astype(str).tolist(),
                        key="par_foco")
    s2.caption(f"Muestra qué **{sub_lbl.lower()}s** explican la merma dentro del elemento "
               "seleccionado. Así se pasa del síntoma a la causa accionable.")
    sub = df[df[col].astype(str) == foco]
    par2 = calcular_pareto(sub, sub_col, metrica, umbral_a=umbral)
    st.plotly_chart(
        grafica_pareto(par2, sub_col, metrica, 12, umbral, f"{foco} → por {sub_lbl.lower()}"),
        key="fig_pareto2",
    )

    # ---- Justificación económica ------------------------------------------
    st.markdown("#### 💰 Ahorro potencial al atacar los pocos vitales")
    dias = max((df["fecha"].max() - df["fecha"].min()).days + 1, 1)
    costo_a = par.loc[par["clase"] == "A", "costo"].sum()
    r1, r2, r3, r4 = st.columns([1.4, 1, 1, 1])
    reduccion = r1.slider("Reducción esperada en la clase A (%)", 10, 80, 40, step=5,
                          key="par_red")
    ahorro = costo_a * reduccion / 100
    r2.metric("Pérdida clase A (periodo)", ui.money(costo_a))
    r3.metric("Ahorro en el periodo", ui.money(ahorro))
    r4.metric("Ahorro anualizado", ui.money(ahorro * 365 / dias),
              f"Base: {dias} días de datos", delta_color="off")


def _tab_analisis(df: pd.DataFrame) -> None:
    if df.empty:
        return _sin_datos()

    # ---- Gráfica de control ------------------------------------------------
    st.markdown("#### 📈 Gráfica de control de la merma diaria (X̄ ± 3σ)")
    diario = (df.groupby(df["fecha"].dt.date)["costo_total"].sum()
              .reindex(pd.date_range(df["fecha"].min(), df["fecha"].max()).date, fill_value=0))
    media, sigma = diario.mean(), diario.std(ddof=1) if len(diario) > 1 else 0
    lsc, lic = media + 3 * sigma, max(media - 3 * sigma, 0)
    fuera = diario[(diario > lsc) | (diario < lic)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(diario.index), y=diario.values, mode="lines+markers",
                             name="Merma diaria", line=dict(color=ui.COLOR_LINEA),
                             hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>"))
    for y, nombre, estilo in [(media, "X̄", "solid"), (lsc, "LSC", "dash"), (lic, "LIC", "dash")]:
        fig.add_hline(y=y, line_dash=estilo, line_color=ui.COLOR_A if nombre != "X̄" else "gray",
                      annotation_text=f"{nombre}: {ui.money(y)}", annotation_position="top left")
    if len(fuera):
        fig.add_trace(go.Scatter(x=list(fuera.index), y=fuera.values, mode="markers",
                                 name="Fuera de control",
                                 marker=dict(color=ui.COLOR_A, size=12, symbol="x")))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.12), yaxis_title="MXN")
    st.plotly_chart(fig, key="fig_control")
    if len(fuera):
        st.warning(f"⚠️ {len(fuera)} día(s) fuera de los límites de control. "
                   "Investiga causas especiales en esas fechas: "
                   + ", ".join(pd.to_datetime(fuera.index).strftime("%d/%m").tolist()[:10]))
    else:
        st.success("✅ El proceso está bajo control estadístico (sin causas especiales).")

    # ---- Tendencia semanal y mapa de calor ---------------------------------
    c1, c2 = st.columns(2)
    semanal = (df.set_index("fecha").groupby("categoria")["costo_total"]
               .resample("W-MON").sum().reset_index())
    fig_t = px.area(semanal, x="fecha", y="costo_total", color="categoria",
                    title="Tendencia semanal por categoría",
                    labels={"costo_total": "MXN", "fecha": "Semana", "categoria": "Categoría"})
    fig_t.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10),
                        legend=dict(orientation="h", y=-0.25))
    c1.plotly_chart(fig_t, key="fig_tend")

    pivote = df.pivot_table(index="departamento", columns="categoria", values="costo_total",
                            aggfunc="sum", fill_value=0)
    pivote = pivote.loc[pivote.sum(axis=1).sort_values(ascending=False).index]
    fig_h = px.imshow(pivote, text_auto=".2s", aspect="auto", color_continuous_scale="Reds",
                      title="Mapa de calor: departamento × categoría (MXN)")
    fig_h.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10),
                        xaxis_title="", yaxis_title="")
    c2.plotly_chart(fig_h, key="fig_heat")

    with st.expander("📊 Más detalle: turno, día de la semana y mapa de árbol"):
        # ---- Patrones por turno y día ------------------------------------------
        c3, c4 = st.columns(2)
        turno = df.groupby("turno", as_index=False)["costo_total"].sum().sort_values("costo_total")
        fig_tu = px.bar(turno, x="costo_total", y="turno", orientation="h",
                        title="Pérdida por turno", labels={"costo_total": "MXN", "turno": ""},
                        color_discrete_sequence=[ui.COLOR_PRIMARIO])
        fig_tu.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        c3.plotly_chart(fig_tu, key="fig_turno")

        dsem = df.assign(dia=df["fecha"].dt.dayofweek).groupby("dia")["costo_total"].sum()
        dsem = dsem.reindex(range(7), fill_value=0)
        fig_d = px.bar(x=DIAS_SEMANA, y=dsem.values, title="Pérdida por día de la semana",
                       labels={"x": "", "y": "MXN"}, color_discrete_sequence=[ui.COLOR_LINEA])
        fig_d.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        c4.plotly_chart(fig_d, key="fig_dia")

        # ---- Mapa de árbol -----------------------------------------------------
        fig_tm = px.treemap(df, path=[px.Constant("Tienda"), "departamento", "producto"],
                            values="costo_total", color="departamento",
                            title="Mapa de árbol de pérdidas: departamento → producto")
        fig_tm.update_traces(hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<extra></extra>")
        fig_tm.update_layout(height=480, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_tm, key="fig_tree")


def _tab_plan(df: pd.DataFrame) -> None:
    acciones = obtener_acciones()
    hoy = date.today()

    if not acciones.empty:
        activas = acciones[acciones["estado"] != "Cancelada"]
        compl = (activas["estado"] == "Completada").sum()
        vencidas = activas[(activas["estado"].isin(["Pendiente", "En proceso"]))
                           & (pd.to_datetime(activas["fecha_compromiso"], errors="coerce").dt.date
                              < hoy)]
        k = st.columns(4)
        k[0].metric("Acciones activas", len(activas))
        k[1].metric("Cumplimiento", f"{compl / len(activas) * 100:.0f}%" if len(activas) else "—")
        k[2].metric("Vencidas", len(vencidas), delta_color="inverse")
        k[3].metric("Ahorro comprometido / año", ui.money(activas["ahorro_estimado"].sum()))

    # ---- Focos clase A sin acción ------------------------------------------
    if not df.empty:
        par_p = calcular_pareto(df, "producto")
        focos_a = par_p.loc[par_p["clase"] == "A", "producto"].tolist()
        cubiertos = set(acciones.loc[acciones["estado"] != "Cancelada", "foco"]) \
            if not acciones.empty else set()
        sin_accion = [p for p in focos_a if p not in cubiertos]
        if sin_accion:
            st.warning("🎯 Productos clase A **sin acción correctiva**: " + ", ".join(sin_accion))
        elif focos_a:
            st.success("✅ Todos los productos clase A tienen al menos una acción asignada.")
    else:
        focos_a = []

    st.markdown("#### ➕ Nueva acción correctiva (PHVA)")
    c1, c2 = st.columns([1, 2])
    tipo = c1.radio("Tipo de foco", ["Producto", "Departamento", "Causa"], horizontal=True,
                    key="acc_tipo")
    if df.empty:
        opciones = []
    elif tipo == "Producto":
        opciones = calcular_pareto(df, "producto")["producto"].tolist()
    elif tipo == "Departamento":
        opciones = calcular_pareto(df, "departamento")["departamento"].tolist()
    else:
        opciones = calcular_pareto(df, "causa")["causa"].tolist()
    foco = c2.selectbox("Foco (ordenado de mayor a menor pérdida)", opciones or ["—"],
                        key="acc_foco",
                        format_func=lambda x: f"⭐ {x}" if x in focos_a else x)

    sugerido = 0.0
    if opciones and foco != "—":
        col = {"Producto": "producto", "Departamento": "departamento", "Causa": "causa"}[tipo]
        dias = max((df["fecha"].max() - df["fecha"].min()).days + 1, 1)
        sugerido = round(df.loc[df[col] == foco, "costo_total"].sum() * 365 / dias * 0.4, -2)

    with st.form("form_accion", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        herramienta = f1.selectbox("Herramienta de mejora", HERRAMIENTAS_MEJORA)
        responsable = f2.text_input("Responsable")
        compromiso = f3.date_input("Fecha compromiso", value=hoy + timedelta(days=14),
                                   format="DD/MM/YYYY")
        accion = st.text_area("Acción a implementar *", height=80,
                              placeholder="Ej. Ajustar el pedido sugerido de plátano con base "
                                          "en la venta promedio de 4 semanas y aplicar FEFO.")
        ahorro = st.number_input("Ahorro anual estimado (MXN)", min_value=0.0, value=sugerido,
                                 step=500.0,
                                 help="Sugerido: 40% de la pérdida anualizada del foco.")
        if st.form_submit_button("Guardar acción", type="primary"):
            if not accion.strip() or foco == "—":
                st.error("Selecciona un foco y describe la acción.")
            else:
                db.execute(
                    """INSERT INTO acciones_mermas (fecha_alta, foco, tipo_foco, herramienta,
                       accion, responsable, fecha_compromiso, estado, ahorro_estimado)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendiente', ?)""",
                    (hoy.isoformat(), foco, tipo, herramienta, accion.strip(),
                     responsable.strip(), compromiso.isoformat(), ahorro),
                )
                _flash("Acción registrada en el plan de mejora.")
                st.rerun()

    if acciones.empty:
        st.caption("Aún no hay acciones registradas.")
        return

    st.markdown("#### 📌 Seguimiento del plan de acción")
    editado = st.data_editor(
        acciones, hide_index=True, key="acc_editor",
        disabled=[c for c in acciones.columns if c != "estado"],
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "estado": st.column_config.SelectboxColumn("Estado", options=ESTADOS_ACCION,
                                                       required=True),
            "ahorro_estimado": st.column_config.NumberColumn("Ahorro/año", format="$%.0f"),
            "fecha_alta": "Alta", "foco": "Foco", "tipo_foco": "Tipo",
            "herramienta": "Herramienta", "accion": "Acción", "responsable": "Responsable",
            "fecha_compromiso": "Compromiso", "fecha_cierre": "Cierre",
        },
    )
    cambios = editado[editado["estado"] != acciones["estado"]]
    if len(cambios) and st.button(f"Guardar {len(cambios)} cambio(s) de estado", type="primary"):
        for _, fila in cambios.iterrows():
            cierre = hoy.isoformat() if fila["estado"] == "Completada" else None
            db.execute("UPDATE acciones_mermas SET estado = ?, fecha_cierre = ? WHERE id = ?",
                       (fila["estado"], cierre, int(fila["id"])))
        _flash("Estados actualizados.")
        st.rerun()


def _tab_datos(df: pd.DataFrame, df_all: pd.DataFrame) -> None:
    st.markdown(f"#### Registros filtrados: {len(df):,}")
    vista = df.copy()
    if not vista.empty:
        vista["fecha"] = vista["fecha"].dt.date
    st.dataframe(
        vista, hide_index=True, height=380,
        column_config={
            "costo_unitario": st.column_config.NumberColumn("Costo unit.", format="$%.2f"),
            "costo_total": st.column_config.NumberColumn("Pérdida", format="$%.2f"),
            "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
        },
    )

    sucursal = st.session_state.get("sucursal", "sucursal").replace(" ", "_")
    stamp = f"{date.today():%Y%m%d}"
    c1, c2 = st.columns(2)
    if not df.empty:
        hojas = {
            "Registros": vista,
            "Pareto productos": calcular_pareto(df, "producto"),
            "Pareto departamentos": calcular_pareto(df, "departamento"),
            "Pareto causas": calcular_pareto(df, "causa"),
            "Plan de accion": obtener_acciones(),
        }
        c1.download_button("⬇️ Reporte Excel (registros + Paretos + plan)", _excel_bytes(hojas),
                           f"mermas_{sucursal}_{stamp}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           type="primary")
        c2.download_button("⬇️ CSV de registros", vista.to_csv(index=False).encode("utf-8-sig"),
                           f"mermas_{sucursal}_{stamp}.csv", "text/csv")

    with st.expander("🗑️ Eliminar registros específicos"):
        ids = st.multiselect("IDs a eliminar", df["id"].tolist() if not df.empty else [],
                             key="del_ids")
        if ids and st.button(f"Eliminar {len(ids)} registro(s)"):
            marcadores = ",".join("?" * len(ids))
            db.execute(f"DELETE FROM mermas WHERE id IN ({marcadores})", [int(i) for i in ids])
            _flash(f"Se eliminaron {len(ids)} registros.")
            st.rerun()

    with st.expander("🛠️ Administración de datos"):
        a1, a2 = st.columns(2)
        if a1.button("🎲 Agregar 90 días de datos de demostración"):
            n = generar_datos_demo()
            _flash(f"Se generaron {n} registros de demostración.")
            st.rerun()
        confirmar = a2.checkbox("Confirmo que quiero borrar TODOS los registros de merma",
                                key="conf_borrar")
        if a2.button("Borrar todo", disabled=not confirmar):
            db.execute("DELETE FROM mermas")
            _flash(f"Se borraron {len(df_all)} registros.", "warning")
            st.session_state.pop("mer_rango", None)
            st.rerun()


# =====================================================================
# Punto de entrada de la página
# =====================================================================
def render() -> None:
    ui.page_header(
        "Análisis de Mermas y Costos",
        "Diagrama de Pareto · Ley 80/20 · Clasificación ABC · Control estadístico · Plan PHVA",
        "📉",
    )
    _mostrar_flash()

    df_all = obtener_mermas()
    productos = obtener_productos()

    if df_all.empty:
        st.info("Todavía no hay mermas registradas. Captura la primera en **Registro** "
                "o genera un escenario de demostración para explorar el módulo.")
        if st.button("🎲 Generar 90 días de datos de demostración", type="primary"):
            n = generar_datos_demo()
            _flash(f"Se generaron {n} registros de demostración.")
            st.rerun()
        df = df_all
    else:
        filtros = _filtros(df_all)
        df = _aplicar(df_all, filtros)
        _kpis(df, df_all, filtros)
        st.caption(f"Periodo analizado: {filtros['ini']:%d/%m/%Y} – {filtros['fin']:%d/%m/%Y}")

    t1, t2, t3, t4, t5 = st.tabs(["📝 Registro", "📊 Pareto", "🔍 Análisis profundo",
                                  "🛠️ Plan de acción", "🗂️ Datos"])
    with t1:
        _tab_registro(productos)
    with t2:
        _tab_pareto(df)
    with t3:
        _tab_analisis(df)
    with t4:
        _tab_plan(df)
    with t5:
        _tab_datos(df, df_all)
