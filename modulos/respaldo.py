"""
Respaldo, restauración y reporte de resultados.

Streamlit Cloud borra el disco al reiniciar o redesplegar la app. Este módulo permite:
    * Descargar un Excel con todas las tablas (respaldo completo).
    * Restaurar ese Excel en una base nueva.
    * Generar la hoja «Resumen» con los resultados de los cuatro módulos para la tesis.
"""

from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from modulos import database as db
from modulos import kaizen, layout, mermas, toc, ui

TABLAS = [
    "productos", "mermas", "acciones_mermas", "tiempos_toc",
    "produccion_turnos", "eventos_kaizen", "ubicaciones_layout",
]


# =====================================================================
# Resumen de resultados (parámetros de referencia de cada módulo)
# =====================================================================
def resumen_resultados() -> pd.DataFrame:
    filas: list[dict] = []

    def add(modulo: str, indicador: str, valor: str) -> None:
        filas.append({"Módulo": modulo, "Indicador": indicador, "Valor": valor})

    # Mermas
    try:
        ini = (date.today() - timedelta(days=89)).isoformat()
        df = db.query_df("SELECT producto, costo_total FROM mermas WHERE fecha >= ?", (ini,))
        if df.empty:
            add("Mermas", "Pérdida en 90 días", "Sin datos")
        else:
            par = mermas.calcular_pareto(mermas.obtener_mermas(), "producto")
            a = par[par["clase"] == "A"]
            add("Mermas", "Pérdida total en 90 días", ui.money(df["costo_total"].sum()))
            add("Mermas", "Producto con mayor pérdida", str(par.iloc[0]["producto"]))
            add("Mermas", "Productos clase A (pocos vitales)",
                f"{len(a)} de {len(par)} ({len(a) / len(par) * 100:.0f}%) "
                f"concentran {a['pct'].sum():.0f}% de la pérdida")
    except Exception as exc:  # noqa: BLE001
        add("Mermas", "Pareto", f"No disponible ({exc})")

    # Cuellos de botella (parámetros de referencia)
    try:
        mu = 60 / 2.5
        c_req = toc.c_minimo(110, mu, 3.0)
        r = toc.mmc(110, mu, c_req or 1)
        add("Cuellos de botella", "Cajas mínimas en pico (110 cl/h, meta 3 min)",
            str(c_req) if c_req else "No alcanzable")
        add("Cuellos de botella", "Espera en fila con esas cajas",
            f"{r['Wq']:.1f} min" if r["stable"] else "Inestable")
        add("Cuellos de botella", "Autos sin cajón (60 cajones, 70 autos/h, 35 min)",
            f"{toc.erlang_b(70 * 35 / 60, 60) * 100:.1f}%")
    except Exception as exc:  # noqa: BLE001
        add("Cuellos de botella", "Modelo", f"No disponible ({exc})")

    # Layout
    try:
        P = layout.PARAM_DEFAULT
        df_l = layout.cargar(P)
        if df_l.empty:
            add("Layout", "Ahorro por reubicación", "Sin datos")
        else:
            prop = layout.propuesta_por_rotacion(df_l, P)
            if prop is None:
                add("Layout", "Ahorro por reubicación", "No caben los productos")
            else:
                actual, nuevo = df_l["metros_dia"].sum(), prop["metros_dia"].sum()
                add("Layout", "Metros diarios de surtido (actual → propuesta)",
                    f"{actual:,.0f} m → {nuevo:,.0f} m ({(actual - nuevo) / actual * 100:.0f}% menos)")
    except Exception as exc:  # noqa: BLE001
        add("Layout", "Ubicación", f"No disponible ({exc})")

    # Kaizen
    try:
        hoy = date.today()
        umbrales = {"verde": 100.0, "amarillo": 90.0, "efic": 90.0}
        df_k = kaizen.cargar(hoy - timedelta(days=29), hoy, umbrales)
        if df_k.empty:
            add("Kaizen", "Cumplimiento 30 días", "Sin datos")
        else:
            for turno, g in df_k.groupby("turno_corto"):
                add("Kaizen", f"Cumplimiento promedio · {turno}",
                    f"{g['cumplimiento'].mean():.0f}% · eficiencia {g['eficiencia'].mean():.0f}% · "
                    f"{(g['semaforo'] == 'Verde').mean() * 100:.0f}% de días en verde")
    except Exception as exc:  # noqa: BLE001
        add("Kaizen", "Indicadores", f"No disponible ({exc})")

    return pd.DataFrame(filas)


# =====================================================================
# Exportar / importar
# =====================================================================
def exportar_excel() -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        resumen_resultados().to_excel(writer, sheet_name="Resumen", index=False)
        for tabla in TABLAS:
            db.query_df(f"SELECT * FROM {tabla}").to_excel(writer, sheet_name=tabla, index=False)
        for hoja in writer.sheets.values():
            for col in hoja.columns:
                ancho = max((len(str(c.value)) for c in col if c.value is not None), default=8)
                hoja.column_dimensions[col[0].column_letter].width = min(max(10, ancho + 2), 50)
    return buffer.getvalue()


def _columnas(conn, tabla: str) -> list[str]:
    return [fila[1] for fila in conn.execute(f"PRAGMA table_info({tabla})").fetchall()]


def _nativo(valor):
    """Convierte tipos de numpy/pandas a tipos que SQLite acepta."""
    if pd.isna(valor):
        return None
    return valor.item() if hasattr(valor, "item") else valor


def importar_excel(archivo) -> dict[str, int]:
    """Reemplaza el contenido de cada tabla con la hoja del mismo nombre."""
    xls = pd.ExcelFile(archivo)
    if "productos" not in xls.sheet_names:
        raise ValueError("El archivo no es un respaldo de OptiBodega (falta la hoja «productos»).")
    conteos: dict[str, int] = {}
    with db.get_conn() as conn:
        for tabla in TABLAS:
            if tabla not in xls.sheet_names:
                continue
            df = pd.read_excel(xls, sheet_name=tabla)
            cols = [c for c in _columnas(conn, tabla) if c in df.columns]
            conn.execute(f"DELETE FROM {tabla}")
            if df.empty or not cols:
                conteos[tabla] = 0
                continue
            datos = [[_nativo(v) for v in fila] for fila in df[cols].itertuples(index=False)]
            marcadores = ", ".join("?" * len(cols))
            conn.executemany(
                f"INSERT INTO {tabla} ({', '.join(cols)}) VALUES ({marcadores})", datos
            )
            conteos[tabla] = len(datos)
    return conteos


# =====================================================================
# Interfaz
# =====================================================================
def render() -> None:
    ui.page_header("Respaldo y reporte de resultados",
                   "Resumen para la tesis · descarga completa · restauración", "💾")
    if "resp_flash" in st.session_state:
        st.success(st.session_state.pop("resp_flash"))

    st.markdown("#### 📑 Resultados de los cuatro módulos")
    st.caption("Calculados con los parámetros de referencia de cada módulo. Para resultados "
               "de tu tienda, ajusta los parámetros en cada pestaña.")
    resumen = resumen_resultados()
    st.dataframe(resumen, hide_index=True, use_container_width=True)

    st.markdown("#### ⬇️ Respaldo completo")
    st.write("Descarga un Excel con todas las tablas y el resumen. Guárdalo: si la app se "
             "reinicia, puedes restaurarlo aquí mismo.")
    sucursal = st.session_state.get("sucursal", "sucursal").replace(" ", "_")
    st.download_button("⬇️ Descargar respaldo (.xlsx)", exportar_excel(),
                       f"respaldo_{sucursal}_{date.today():%Y%m%d}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       type="primary")

    st.markdown("#### ⬆️ Restaurar respaldo")
    st.warning("Restaurar reemplaza TODOS los datos actuales por los del archivo.")
    archivo = st.file_uploader("Archivo de respaldo", type=["xlsx"], key="resp_upload")
    confirmar = st.checkbox("Confirmo reemplazar los datos actuales", key="resp_conf")
    if archivo is not None and st.button("♻️ Restaurar", disabled=not confirmar):
        try:
            conteos = importar_excel(archivo)
            detalle = ", ".join(f"{t}: {n:,}" for t, n in conteos.items())
            st.session_state["resp_flash"] = f"Respaldo restaurado ({detalle})."
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"No se pudo restaurar: {exc}")
