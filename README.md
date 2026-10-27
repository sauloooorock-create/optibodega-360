# 🏪 OptiBodega 360

Sistema web de **mejora continua y optimización operativa en tiempo real** para una tienda de autoservicio.
Proyecto de tesis de Ingeniería Industrial y de Sistemas, desarrollado en Python + Streamlit.

## Estructura

```
optibodega-360/
├── app.py                  # Punto de entrada: configuración, navegación y arranque de la BD
├── requirements.txt        # Dependencias para Streamlit Cloud
├── .streamlit/config.toml  # Tema y configuración del servidor
├── .gitignore
├── data/                   # Aquí se crea optibodega.db (SQLite) al arrancar
└── modulos/
    ├── database.py         # Conexión, esquema SQLite y funciones de consulta
    ├── catalogos.py        # Departamentos, productos, causas, turnos, motivos de paro
    ├── ui.py               # Estilos y componentes visuales compartidos
    ├── inicio.py           # Portada: resumen, Pareto de mermas y estado de los módulos
    ├── toc.py              # Módulo 1 · Cuellos de botella y logística (TOC)
    ├── mermas.py           # Módulo 2 · Mermas y costos (Pareto 80/20)
    ├── layout.py           # Módulo 3 · Layout y recorridos (rutas, ABC, operaciones)
    ├── kaizen.py           # Módulo 4 · Cuadro de mando Kaizen (KPIs por turno)
    ├── respaldo.py         # Respaldo, restauración y reporte de resultados
    └── proximamente.py     # Fichas de módulos futuros (reserva)
```

## Módulos

### 1 · Cuellos de botella y logística (`toc.py`)

| Pestaña | Qué hace | Herramienta de IE |
|---|---|---|
| Cajas | Espera según cajas abiertas, cajas mínimas para la meta, perfil horario del día y simulación de eventos discretos | Teoría de colas M/M/c (Erlang C), simulación |
| Estacionamiento | Autos que no encuentran cajón, ocupación y Ley de Little | Erlang B, Ley de Little |
| Recibo | Espera del camión según andenes y andenes necesarios | Teoría de colas M/M/c |
| Restricción | Carga relativa de cada subsistema, cuello de botella y los 5 pasos | Teoría de Restricciones (TOC) |
| Datos | Registro de tiempos observados, resumen por área y por hora | Recolección de datos |

### 2 · Mermas y costos (`mermas.py`)

| Pestaña | Qué hace | Herramienta de IE |
|---|---|---|
| Registro | Captura individual (catálogo con costo automático) y carga masiva CSV/Excel | Hoja de verificación |
| Pareto | Pareto por producto, departamento, categoría, causa o turno; clasificación ABC; Pareto de 2.º nivel; ahorro anualizado | Diagrama de Pareto 80/20 |
| Análisis profundo | Gráfica de control X̄ ± 3σ, tendencia semanal, mapa de calor, patrones por turno y día, mapa de árbol | Control estadístico, estratificación |
| Plan de acción | Acciones correctivas ligadas a los focos clase A, seguimiento de estado | Ciclo PHVA |
| Datos | Reporte Excel multi-hoja, CSV, borrado y datos de demostración | — |

### 3 · Layout y recorridos (`layout.py`)

| Pestaña | Qué hace | Herramienta de IE |
|---|---|---|
| Plano y ruta | Plano del piso, lista de surtido y ruta actual vs. vecino más cercano vs. 2-opt | Distancia rectilínea, heurísticas del viajero |
| Distancias | Distancia de cada pasillo y de cada producto al almacén | Análisis de distancias |
| Rotación (ABC) | Reubicación por frecuencia de surtido y ahorro de metros diarios | Clasificación ABC, ubicación por rotación |
| Operaciones | Diagrama de operaciones y recorrido con simbología ASME y % de tiempo sin valor | Diagrama de operaciones y recorridos (ASME) |
| Datos | Ubicaciones editables y demostración | — |

Modelo de distancias: el almacén está en el origen y un pasillo principal corre a lo largo del piso. Dos puntos en el mismo pasillo están a `|y1 − y2|`; en pasillos distintos, a `y1 + |x1 − x2| + y2` (bajar al pasillo principal, cruzar y subir).

### 4 · Cuadro de mando Kaizen (`kaizen.py`)

| Pestaña | Qué hace | Herramienta de IE |
|---|---|---|
| Panel del día | Semáforo Verde/Amarillo/Rojo por turno, medidores de cumplimiento y eficiencia | Gestión visual (Andon), KPIs |
| Tendencias | Cumplimiento y eficiencia por día y turno | Control de procesos |
| Tiempos muertos | Pareto de paros por causa y mapa de calor turno × causa | Pareto, estratificación |
| Registro | Captura por turno (un registro por día y turno), demostración y administración | — |
| Kaizen | Bitácora de mejoras con la causa atacada y el resultado medido | Ciclo PHVA, Kaizen |

Indicadores:
- **Cumplimiento** = transacciones reales ÷ meta × 100
- **Productividad** = transacciones ÷ (colaboradores × horas)
- **Eficiencia operativa** = (tiempo planeado − minutos muertos) ÷ tiempo planeado × 100

## Ejecutar localmente

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Documentación

- [`docs/MANUAL_USUARIO.md`](docs/MANUAL_USUARIO.md): cómo operar cada módulo y leer sus indicadores.
- [`docs/GUION_DEMO.md`](docs/GUION_DEMO.md): guion de 8 minutos para la defensa, con preguntas probables del jurado.

## Pruebas de los modelos

Validan las fórmulas de colas (M/M/1 y Erlang C), Erlang B, la simulación contra el modelo,
la distancia rectilínea, la mejora 2-opt contra la ruta óptima por fuerza bruta, el semáforo
Kaizen y la ida y vuelta del respaldo.

```bash
python tests/test_modelos.py     # sin dependencias extra
# o, con pytest instalado:  pytest tests
```

Página **Respaldo y reporte**: descarga un Excel con todas las tablas y la hoja de resumen,
y permite restaurarlo si la app se reinicia.

## Desplegar en Streamlit Cloud

1. Sube esta carpeta a un repositorio de GitHub (la raíz del repo debe contener `app.py`).
2. En share.streamlit.io elige **New app**, selecciona el repo, la rama `main` y escribe `app.py` como archivo principal.
3. Listo: la base de datos y el catálogo se crean solos en el primer arranque.

> **Importante sobre los datos en la nube:** el disco de Streamlit Cloud es temporal. Cuando la
> app se reinicia o se vuelve a desplegar, `data/optibodega.db` se recrea vacía. Para la
> presentación usa el botón **Cargar escenario de demostración** de la portada y descarga el
> reporte Excel como respaldo. Todo el acceso a datos pasa por `modulos/database.py`, así que
> conectar una base externa no requiere cambiar los módulos.

## Hoja de ruta

- [x] Arquitectura modular, base de datos y navegación
- [x] Módulo 1 · Cuellos de botella (TOC, colas M/M/c, simulación)
- [x] Módulo 2 · Mermas y costos (Pareto 80/20)
- [x] Módulo 3 · Layout y recorridos (distancias rectilíneas, 2-opt, reubicación ABC)
- [x] Módulo 4 · Cuadro de mando Kaizen (KPIs por turno)
- [x] Respaldo y restauración desde la app, reporte de resultados y pruebas de los modelos
- [ ] Base de datos externa para persistencia en la nube
