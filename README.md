# 🏪 OptiBodega 360

Sistema web de **mejora continua y optimización operativa en tiempo real** para una tienda de autoservicio.
Proyecto de tesis de Ingeniería Industrial y de Sistemas, desarrollado en Python + Streamlit.

## Estructura

```
optibodega/
├── app.py                  # Punto de entrada: configuración, navegación y arranque de la BD
├── requirements.txt        # Dependencias para Streamlit Cloud
├── .streamlit/config.toml  # Tema y configuración del servidor
├── data/                   # Aquí se crea optibodega.db (SQLite) al arrancar
└── modulos/
    ├── __init__.py         # Metadatos del paquete
    ├── database.py         # Conexión, esquema SQLite y funciones de consulta
    ├── catalogos.py        # Departamentos, productos, causas raíz, turnos, herramientas
    ├── ui.py               # Estilos y componentes visuales compartidos
    ├── inicio.py           # Página de inicio y resumen ejecutivo
    ├── mermas.py           # Módulo 2 · Mermas y Costos (Pareto)   ✅ operativo
    └── proximamente.py     # Fichas de TOC, Layout y Kaizen       🚧 siguientes etapas
```

## Módulo de Mermas y Costos

| Pestaña | Qué hace | Herramienta de IE |
|---|---|---|
| Registro | Captura individual (catálogo con costo automático) y carga masiva CSV/Excel | Hoja de verificación |
| Pareto | Pareto por producto, departamento, categoría, causa o turno; por costo o frecuencia; clasificación ABC; Pareto de 2.º nivel; ahorro anualizado | Diagrama de Pareto 80/20 |
| Análisis profundo | Gráfica de control X̄ ± 3σ, tendencia semanal, mapa de calor, patrones por turno y día, mapa de árbol | Control estadístico de procesos, estratificación |
| Plan de acción | Acciones correctivas ligadas a los focos clase A, alertas de focos sin atender, seguimiento de estado | Ciclo PHVA |
| Datos | Consulta, reporte Excel multi-hoja, CSV, borrado y datos de demostración | — |

## Ejecutar localmente

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Desplegar en Streamlit Cloud

1. Sube esta carpeta a un repositorio de GitHub (la raíz del repo debe contener `app.py`).
2. En share.streamlit.io elige **New app**, selecciona el repo y escribe `app.py` como archivo principal.
3. Listo: la base de datos y el catálogo se crean solos en el primer arranque.

> **Importante sobre los datos en la nube:** el disco de Streamlit Cloud es temporal. Cuando la
> app se reinicia o se vuelve a desplegar, `data/optibodega.db` se recrea vacía. Para la
> presentación usa el botón de datos de demostración y descarga el reporte Excel como respaldo.
> En una etapa posterior se puede conectar una base de datos externa sin cambiar los módulos,
> porque todo el acceso a datos pasa por `modulos/database.py`.

## Hoja de ruta

- [x] Arquitectura modular, base de datos y navegación
- [x] Módulo 2 · Mermas y Costos (Pareto)
- [ ] Módulo 1 · Cuellos de botella (TOC, colas M/M/c, simulación)
- [ ] Módulo 3 · Layout y recorridos (distancias rectilíneas, ruta óptima)
- [ ] Módulo 4 · Cuadro de mando Kaizen (KPIs por turno)
