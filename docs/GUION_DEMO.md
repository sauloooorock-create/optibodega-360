# Guion de demostración para la defensa (≈ 8 minutos)

Objetivo: mostrar que la app convierte datos de la tienda en decisiones con herramientas de
Ingeniería Industrial. Cada bloque abre con la pregunta que responde.

**Antes de empezar (5 min antes):**
1. Abre la app en el proyector y pulsa **Cargar escenario de demostración** en la portada, si está vacía.
2. Ten a la mano el respaldo `.xlsx` como plan B: restáuralo desde **Respaldo y reporte**.
3. Deja abiertos los paneles **⚙️ Parámetros** cerrados; los abres durante la demo.

---

## 1 · Portada (1 min)

> «El sistema concentra los cuatro módulos. La portada muestra el Pareto de pérdidas: ya desde
> aquí se ve que pocos productos explican la mayor parte del costo.»

Señala la gráfica de Pareto y el texto de interpretación.

## 2 · Cuellos de botella (2 min) · ¿dónde se forman las colas?

1. Pestaña **Cajas**: «Con 4 cajas y 110 clientes por hora, la espera promedio es de X min.»
   Mueve **Cajas abiertas** y muestra cómo cae la espera.
2. Señala la línea **Cajas necesarias** del perfil del día: «Las horas pico necesitan más cajas
   que el resto del día. Abrir cajas por horario es más barato que abrirlas todo el día.»
3. Opcional: pulsa **Ejecutar simulación** con 8 horas y compara con el modelo.
4. Pestaña **Restricción**: «El subsistema con mayor carga es la restricción. Mejorar otra cosa
   no aumenta el flujo de la tienda.»

## 3 · Mermas y costos (2 min) · ¿qué productos pierden más dinero?

1. Pestaña **Pareto**: muestra los pocos vitales en rojo.
2. Baja al **Pareto de segundo nivel**: «Dentro de la carne, la causa principal es X.»
3. Pestaña **Plan de acción**: «La app avisa qué productos clase A aún no tienen acción. Aquí
   registramos la acción con su herramienta de mejora.»

## 4 · Layout y recorridos (1.5 min) · ¿cuánto camina el surtidor?

1. Pestaña **Plano y ruta**: compara **Ruta actual** contra **2-opt (mejorada)**.
   «El mismo pedido, en el orden mejorado, camina X % menos.»
2. Pestaña **Rotación (ABC)**: «Si movemos los productos de mayor rotación cerca del almacén,
   ahorramos X metros al día.»

## 5 · Cuadro de mando Kaizen (1.5 min) · ¿cómo va cada turno?

1. Pestaña **Panel del día**: señala los semáforos. «El turno nocturno está en amarillo o rojo
   porque tiene más tiempos muertos.»
2. Pestaña **Tiempos muertos**: el Pareto de paros muestra la causa principal.
3. Pestaña **Kaizen**: «Cada mejora registra la causa atacada y el resultado medido. Así se
   cierra el ciclo PHVA.»

## 6 · Cierre (30 s)

> «Los modelos están validados: la mejora 2-opt llega a la ruta óptima en los casos de prueba,
> y la simulación de colas converge al modelo analítico. Las pruebas están en el repositorio y
> el manual de usuario en `docs/`.»

Abre **Respaldo y reporte** y muestra la tabla de resultados para la tesis.

---

## Preguntas probables del jurado

| Pregunta | Respuesta corta |
|---|---|
| ¿Los datos son reales? | Son simulados con patrones realistas. El sistema está listo para cargar datos reales por captura o por CSV/Excel. |
| ¿El modelo de colas supone llegadas Poisson? | Sí, es M/M/c. Para horas pico con llegadas más regulares, la espera real es menor; la simulación permite probarlo. |
| ¿La distancia es real? | Es rectilínea sobre una red de pasillos. Sirve para comparar escenarios; no es un recorrido medido con GPS. |
| ¿Qué pasa con los datos al reiniciar? | Hay respaldo y restauración desde la app. La base externa queda como trabajo futuro. |
| ¿Por qué 2-opt y no un algoritmo exacto? | Con 25 paradas el problema es NP-difícil; 2-opt da soluciones muy cercanas al óptimo en tiempos razonables, y lo verificamos por fuerza bruta en casos pequeños. |
