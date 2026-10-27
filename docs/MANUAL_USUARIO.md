# Manual de usuario · OptiBodega 360

Guía para operar el sistema de mejora continua de una tienda de autoservicio. Describe qué
hace cada módulo, cómo se usa y qué significa cada indicador.

---

## 1. Primeros pasos

1. Abre la app. La portada muestra el resumen de los últimos 30 días y las tarjetas de cada módulo.
2. Si la portada aparece vacía, pulsa **🎲 Cargar escenario de demostración**. Carga datos simulados de una tienda para que explores el sistema sin captura previa.
3. En el menú lateral escribe el nombre de tu **sucursal**. Aparece en reportes y exportaciones.
4. Cada módulo tiene un panel **⚙️ Parámetros** (colapsado). Ahí ajustas los números a tu tienda: cajas, cajones, andenes, metas, velocidad de caminata. Los resultados cambian en vivo.

> **Antes de cerrar una sesión de captura:** ve a **Respaldo y reporte** y descarga el respaldo.
> La app puede reiniciarse y los datos del disco se pierden. El respaldo permite restaurarlos.

---

## 2. Cuellos de botella y logística

Responde: ¿dónde se forman las colas y qué limita el flujo de la tienda?

| Pestaña | Para qué sirve | Cómo usarla |
|---|---|---|
| **Cajas** | Espera en fila según el número de cajas | Captura los clientes por hora (pico) y el tiempo de servicio. La gráfica muestra la espera según cajas abiertas. La línea «Cajas necesarias» indica cuántas cajas hacen falta cada hora. |
| **Estacionamiento** | Autos que no encuentran cajón | Captura cajones, autos por hora y estancia promedio. Si más del 5 % no entra, la app indica cuántos cajones se necesitan. |
| **Recibo** | Espera de camiones en andenes | Captura andenes, camiones por hora y minutos de descarga. |
| **Restricción** | Cuello de botella de la tienda | Compara la carga de cajas, estacionamiento y recibo. El subsistema con mayor carga es la restricción: limita a toda la tienda. |
| **Datos** | Tiempos reales observados | Registra tiempos medidos con cronómetro para compararlos con el modelo. |

**Simulación:** en la pestaña Cajas, el botón **▶️ Ejecutar simulación** corre llegadas y servicios aleatorios. Con pocas horas la espera queda por debajo del modelo, porque la fila arranca vacía. Con 8 horas o más los dos valores se acercan.

---

## 3. Mermas y costos

Responde: ¿qué productos y departamentos generan más pérdida económica?

| Pestaña | Para qué sirve |
|---|---|
| **Registro** | Captura una merma (producto, categoría, causa, cantidad y responsable). El costo se llena solo desde el catálogo. También admite carga masiva desde CSV o Excel con la plantilla. |
| **Pareto** | Ordena las pérdidas de mayor a menor y marca los **pocos vitales** (clase A, el 80 % de la pérdida). Puedes cambiar la dimensión: producto, departamento, categoría, causa o turno. |
| **Análisis profundo** | Gráfica de control de la merma diaria (límites ± 3σ), tendencia semanal, mapa de calor departamento × categoría y mapa de árbol. |
| **Plan de acción** | Registra acciones correctivas (ciclo PHVA) ligadas a los productos clase A. La app avisa qué focos clase A no tienen acción asignada. |
| **Datos** | Reporte Excel con registros, Paretos y plan de acción. |

**Lectura del Pareto:** si la clase A tiene pocos elementos y concentra la mayoría de la pérdida, aplica el principio 80/20 y concentra los recursos ahí. Si la distribución es uniforme, el Pareto no ayuda: estratifica por otra dimensión.

---

## 4. Layout y recorridos

Responde: ¿cuánto camina el surtidor y cómo se reduce?

Supuestos del modelo: el almacén está en el origen. Un pasillo principal recorre la tienda y de él salen los pasillos de venta. La distancia entre dos puntos es rectilínea: si están en el mismo pasillo, es la diferencia de posición; si están en pasillos distintos, se baja al pasillo principal, se cruza y se sube.

| Pestaña | Para qué sirve |
|---|---|
| **Plano y ruta** | Genera una lista de surtido y compara tres rutas: la actual (en el orden de captura), la del vecino más cercano y la mejorada con 2-opt. |
| **Distancias** | Muestra la distancia de cada pasillo y de cada producto al almacén. |
| **Rotación (ABC)** | Propone mover los productos de mayor frecuencia de surtido cerca del almacén y calcula los metros diarios que se ahorran. Puedes aplicar la propuesta. |
| **Operaciones** | Diagrama de operaciones y recorrido con simbología ASME: operación (○), transporte (→), inspección (□) y demora (D). Muestra qué porcentaje del surtido es transporte o espera. |
| **Datos** | Ubicaciones editables (pasillo y posición) y demostración. |

**Cómo leer el ahorro:** la métrica es la distancia de ida y vuelta por cada surtido, multiplicada por la frecuencia diaria. Es una estimación para comparar escenarios, no un recorrido medido con GPS.

---

## 5. Cuadro de mando Kaizen

Responde: ¿cómo va cada turno frente a su meta y qué mejoras se han hecho?

### Indicadores

- **Cumplimiento** = transacciones reales ÷ meta × 100.
- **Productividad** = transacciones ÷ (colaboradores × horas). Sirve para comparar turnos de distinto tamaño.
- **Eficiencia operativa** = (tiempo planeado − minutos muertos) ÷ tiempo planeado × 100.

### Semáforo

| Color | Condición (valores por defecto) |
|---|---|
| 🟢 Verde | Cumplimiento ≥ 100 % **y** eficiencia ≥ 90 % |
| 🟡 Amarillo | Cumplimiento ≥ 90 % (y no es verde) |
| 🔴 Rojo | Cumplimiento < 90 % |

Los umbrales y las metas por turno se ajustan en **⚙️ Metas y umbrales del semáforo**.

### Pestañas

- **Panel del día:** semáforo, medidores y el turno con mayor brecha. Elige el día en el selector.
- **Tendencias:** evolución por día y turno, y porcentaje de días en verde.
- **Tiempos muertos:** Pareto de paros por causa y mapa de calor turno × causa.
- **Registro:** captura un turno. Si ya existía ese día y turno, se actualiza (no se duplica).
- **Kaizen:** bitácora de mejoras con la causa atacada y el resultado medido. Cada mejora debe tener un resultado medible.

---

## 6. Respaldo y reporte

- **Descargar respaldo (.xlsx):** todas las tablas en un solo archivo, más la hoja **Resumen** con los resultados de los cuatro módulos.
- **Restaurar respaldo:** reemplaza todos los datos actuales por los del archivo. Pide confirmación porque no se puede deshacer.

---

## 7. Preguntas frecuentes

**¿Por qué la app se ve vacía después de un rato?**
Streamlit Cloud reinicia la app cuando se duerme por inactividad, al volver a desplegarla, o cuando se reinicia el servidor. El disco es temporal, así que los datos se pierden. Restaura el último respaldo o carga la demostración.

**¿Los resultados de la portada y de los módulos coinciden?**
La portada usa los datos reales de mermas de los últimos 30 días. Cada módulo usa su propio periodo y sus propios parámetros, por eso pueden diferir.

**¿Cómo cambio los parámetros para mi tienda?**
En cada módulo, abre el panel **⚙️ Parámetros**. Los valores por defecto son de referencia y están pensados para una tienda mediana.

**Un dato aparece como «Sin datos».**
Ese módulo aún no tiene registros para el periodo. Captura datos o carga la demostración.
