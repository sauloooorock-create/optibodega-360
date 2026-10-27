"""
Pruebas de los modelos de Ingeniería Industrial de OptiBodega 360.

Ejecutar con pytest:   pytest tests
O sin pytest:          python tests/test_modelos.py
"""
import itertools
import math
import os
import random
import sys
import tempfile
from pathlib import Path

if __name__ == "__main__":  # permite ejecutarlo directo
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import conftest  # noqa: F401,E402  (configura el camino y el doble de Streamlit)

import numpy as np  # noqa: E402

from modulos import database as db  # noqa: E402
from modulos import kaizen, layout, respaldo, toc  # noqa: E402

ORIGEN = (0.0, 0.0, "Almacén")


def test_mm1_coincide_con_formula_cerrada():
    # M/M/1: Wq = ρ / (μ − λ). Con λ=5, μ=6 por hora → 50 min.
    r = toc.mmc(5, 6, 1)
    assert math.isclose(r["Wq"], 50.0, rel_tol=1e-9)
    assert math.isclose(r["rho"], 5 / 6, rel_tol=1e-9)


def test_erlang_c_valor_clasico():
    # λ=2, μ=1, c=3 → probabilidad de esperar ≈ 0.4444 (tabla clásica)
    assert math.isclose(toc.mmc(2, 1, 3)["Pw"], 0.4444, abs_tol=1e-4)


def test_sobrecarga_es_inestable():
    assert toc.mmc(200, 24, 2)["stable"] is False


def test_erlang_b_valores_conocidos():
    assert math.isclose(toc.erlang_b(1, 1), 0.5, rel_tol=1e-12)
    assert math.isclose(toc.erlang_b(5, 10), 0.0184, abs_tol=1e-4)


def test_simulacion_converge_al_modelo():
    # Con tráfico alto (ρ ≈ 0.92) el estado estable tarda en alcanzarse y la simulación es
    # ruidosa: se usan 30 corridas de 40 h y una tolerancia de 15 %.
    rng = np.random.default_rng(1)
    sim = np.concatenate([toc.simular_espera(110, 2.5, 5, 40.0, rng) for _ in range(30)])
    modelo = toc.mmc(110, 24, 5)["Wq"]
    assert abs(sim.mean() - modelo) / modelo < 0.15


def test_distancia_rectilinea():
    assert layout.dist(ORIGEN, (4.0, 10.0, "p")) == 14.0
    assert layout.dist((4.0, 2.0, "a"), (4.0, 9.0, "b")) == 7.0
    assert layout.dist((4.0, 3.0, "a"), (9.0, 5.0, "b")) == 13.0


def test_2opt_llega_al_optimo_en_casos_pequenos():
    rnd = random.Random(3)
    for _ in range(5):
        paradas = [(float(rnd.choice([4, 9, 14, 19, 24])), float(rnd.randrange(1, 20, 2)), f"s{i}")
                   for i in range(7)]
        nn = layout.ruta_vecino_mas_cercano(paradas)
        mejora = layout.mejorar_2opt(nn)
        optimo = min(layout.longitud([ORIGEN] + list(p) + [ORIGEN])
                     for p in itertools.permutations(paradas))
        assert layout.longitud(mejora) <= layout.longitud(nn) + 1e-9
        assert math.isclose(layout.longitud(mejora), optimo, rel_tol=1e-9)


def test_semaforo_kaizen():
    import pandas as pd
    df = pd.DataFrame([
        {"fecha": "2026-10-20", "turno": "Matutino (07–15 h)", "meta": 100.0, "real": 105.0,
         "colaboradores": 5, "horas": 8.0, "minutos_muertos": 10.0, "motivo_muerto": "Otro"},
        {"fecha": "2026-10-20", "turno": "Nocturno (23–07 h)", "meta": 100.0, "real": 80.0,
         "colaboradores": 5, "horas": 8.0, "minutos_muertos": 200.0, "motivo_muerto": "Otro"},
    ])
    k = kaizen.calcular_kpis(df, 100, 90, 90)
    assert list(k["semaforo"]) == ["Verde", "Rojo"]


def test_respaldo_ida_y_vuelta():
    """Exportar y restaurar debe dejar las mismas filas."""
    original = db.DB_PATH
    with tempfile.TemporaryDirectory() as tmp:
        db.DB_PATH = Path(tmp) / "prueba.db"
        try:
            db.init_db()
            from modulos import mermas
            mermas.generar_datos_demo(n=40, dias=10, semilla=5)
            antes = db.contar("mermas")
            archivo = Path(tmp) / "respaldo.xlsx"
            archivo.write_bytes(respaldo.exportar_excel())
            db.execute("DELETE FROM mermas")
            assert db.contar("mermas") == 0
            conteos = respaldo.importar_excel(str(archivo))
            assert conteos["mermas"] == antes
            assert db.contar("mermas") == antes
        finally:
            db.DB_PATH = original


if __name__ == "__main__":
    fallos = 0
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {nombre}")
            except Exception as exc:  # noqa: BLE001
                fallos += 1
                print(f"❌ {nombre}: {exc!r}")
    print("Todas las pruebas pasaron." if not fallos else f"{fallos} prueba(s) fallaron.")
    sys.exit(1 if fallos else 0)
