"""
Capa de datos: SQLite local en data/optibodega.db.

Todas las tablas del sistema se declaran aquí para que cada módulo nuevo
(TOC, Layout, Kaizen) solo agregue su bloque de esquema y reutilice las
funciones `query_df`, `execute` y `executemany`.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from modulos.catalogos import productos_planos

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "optibodega.db"

SCHEMA = """
-- ---------------------------------------------------------------
-- Catálogo de productos (maestro)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS productos (
    sku             TEXT PRIMARY KEY,
    producto        TEXT NOT NULL,
    departamento    TEXT NOT NULL,
    unidad          TEXT NOT NULL,
    costo_unitario  REAL NOT NULL CHECK (costo_unitario >= 0)
);

-- ---------------------------------------------------------------
-- Módulo 2 · Registro de mermas
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mermas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT NOT NULL,              -- YYYY-MM-DD
    turno           TEXT,
    departamento    TEXT NOT NULL,
    sku             TEXT,
    producto        TEXT NOT NULL,
    categoria       TEXT NOT NULL,              -- Caducidad, Daño, Manejo...
    causa           TEXT,                       -- causa raíz
    cantidad        REAL NOT NULL CHECK (cantidad > 0),
    unidad          TEXT,
    costo_unitario  REAL NOT NULL CHECK (costo_unitario >= 0),
    costo_total     REAL NOT NULL,
    responsable     TEXT,
    observaciones   TEXT,
    origen          TEXT DEFAULT 'manual',      -- manual | carga_masiva | demo
    creado_en       TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_mermas_fecha  ON mermas (fecha);
CREATE INDEX IF NOT EXISTS idx_mermas_depto  ON mermas (departamento);

-- ---------------------------------------------------------------
-- Módulo 2 · Plan de acción (ciclo PHVA sobre los pocos vitales)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS acciones_mermas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_alta        TEXT NOT NULL,
    foco              TEXT NOT NULL,            -- producto/departamento atacado
    tipo_foco         TEXT NOT NULL,            -- Producto | Departamento | Causa
    herramienta       TEXT,
    accion            TEXT NOT NULL,
    responsable       TEXT,
    fecha_compromiso  TEXT,
    estado            TEXT NOT NULL DEFAULT 'Pendiente',
    ahorro_estimado   REAL DEFAULT 0,
    fecha_cierre      TEXT
);
"""


@contextmanager
def get_conn():
    """Conexión SQLite con commit automático y cierre garantizado."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Crea las tablas si no existen y siembra el catálogo de productos."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        total = conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
        if total == 0:
            conn.executemany(
                """INSERT INTO productos (sku, producto, departamento, unidad, costo_unitario)
                   VALUES (:sku, :producto, :departamento, :unidad, :costo_unitario)""",
                productos_planos(),
            )


def query_df(sql: str, params: Sequence | dict = ()) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def execute(sql: str, params: Sequence | dict = ()) -> int:
    """Ejecuta una sentencia y devuelve el id de la última fila insertada."""
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def executemany(sql: str, rows: Iterable[Sequence | dict]) -> int:
    with get_conn() as conn:
        cur = conn.executemany(sql, rows)
        return cur.rowcount


def contar(tabla: str) -> int:
    with get_conn() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
