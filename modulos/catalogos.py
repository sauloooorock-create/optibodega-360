"""
Catálogos maestros de la tienda de autoservicio.

Se usan para:
  * poblar la tabla `productos` la primera vez que arranca la app,
  * alimentar las listas desplegables de los formularios,
  * generar datos de demostración realistas.

Los costos son precios de costo aproximados (MXN) con fines académicos.
"""

# Departamento -> lista de (SKU, producto, unidad, costo unitario MXN)
DEPARTAMENTOS: dict[str, list[tuple[str, str, str, float]]] = {
    "Frutas y Verduras": [
        ("FV001", "Plátano Tabasco", "kg", 14.5),
        ("FV002", "Jitomate saladet", "kg", 22.0),
        ("FV003", "Aguacate Hass", "kg", 58.0),
        ("FV004", "Papa blanca", "kg", 24.0),
        ("FV005", "Cebolla blanca", "kg", 19.0),
        ("FV006", "Limón sin semilla", "kg", 28.0),
        ("FV007", "Lechuga romana", "pza", 16.0),
        ("FV008", "Fresa", "kg", 65.0),
    ],
    "Carnes y Pescados": [
        ("CP001", "Pechuga de pollo", "kg", 98.0),
        ("CP002", "Bistec de res", "kg", 165.0),
        ("CP003", "Carne molida de res", "kg", 135.0),
        ("CP004", "Chuleta de cerdo", "kg", 95.0),
        ("CP005", "Filete de tilapia", "kg", 110.0),
    ],
    "Lácteos y Refrigerados": [
        ("LR001", "Leche entera 1 L", "pza", 26.0),
        ("LR002", "Yogurt bebible 1 kg", "pza", 34.0),
        ("LR003", "Queso panela 400 g", "pza", 62.0),
        ("LR004", "Crema ácida 450 ml", "pza", 38.0),
        ("LR005", "Huevo blanco 18 pzas", "pza", 58.0),
    ],
    "Panadería y Tortillería": [
        ("PT001", "Bolillo", "pza", 2.2),
        ("PT002", "Pan dulce surtido", "pza", 9.0),
        ("PT003", "Tortilla de maíz", "kg", 22.0),
        ("PT004", "Pastel tres leches", "pza", 185.0),
    ],
    "Salchichonería": [
        ("SA001", "Jamón de pavo", "kg", 120.0),
        ("SA002", "Salchicha viena", "kg", 78.0),
        ("SA003", "Queso amarillo rebanado", "kg", 140.0),
    ],
    "Abarrotes": [
        ("AB001", "Aceite vegetal 1 L", "pza", 38.0),
        ("AB002", "Arroz 1 kg", "pza", 29.0),
        ("AB003", "Frijol negro 1 kg", "pza", 36.0),
        ("AB004", "Atún en lata 140 g", "pza", 19.0),
        ("AB005", "Galletas surtidas", "pza", 32.0),
    ],
    "Bebidas": [
        ("BE001", "Refresco 2 L", "pza", 34.0),
        ("BE002", "Agua natural 1.5 L", "pza", 14.0),
        ("BE003", "Jugo de fruta 1 L", "pza", 27.0),
        ("BE004", "Cerveza six pack", "pza", 105.0),
    ],
    "Limpieza y Hogar": [
        ("LH001", "Detergente en polvo 1 kg", "pza", 42.0),
        ("LH002", "Cloro 1 L", "pza", 18.0),
        ("LH003", "Papel higiénico 12 rollos", "pza", 79.0),
    ],
    "Mercancías Generales": [
        ("MG001", "Vaso de vidrio", "pza", 25.0),
        ("MG002", "Juguete surtido", "pza", 149.0),
        ("MG003", "Foco LED", "pza", 45.0),
    ],
}

# Categoría de merma -> causas raíz típicas (base para análisis de causa-efecto)
CAUSAS_POR_CATEGORIA: dict[str, list[str]] = {
    "Caducidad": [
        "Sobreinventario / pedido excesivo",
        "Rotación PEPS/FEFO no aplicada",
        "Pronóstico de demanda deficiente",
        "Cadena de frío interrumpida",
    ],
    "Daño": [
        "Daño en transporte del proveedor",
        "Daño en exhibición / anaquel",
        "Empaque defectuoso",
        "Plagas",
    ],
    "Manejo": [
        "Mal estibado en almacén",
        "Golpe con patín o montacargas",
        "Manipulación del cliente",
        "Temperatura de almacenamiento inadecuada",
    ],
    "Faltante (merma desconocida)": [
        "Robo hormiga",
        "Error en recepción de mercancía",
        "Error de cobro en caja",
    ],
    "Calidad de proveedor": [
        "Producto fuera de especificación",
        "Entrega con vida útil corta",
    ],
}

CATEGORIAS_MERMA: list[str] = list(CAUSAS_POR_CATEGORIA.keys())

TURNOS: list[str] = [
    "Matutino (07–15 h)",
    "Vespertino (15–23 h)",
    "Nocturno (23–07 h)",
]

UNIDADES: list[str] = ["pza", "kg", "caja", "L"]

# Causas de tiempo muerto en un turno (base del Pareto de paros)
MOTIVOS_MUERTO: list[str] = [
    "Falta de personal",
    "Falla de equipo (cajas, básculas, lector)",
    "Espera de mercancía o reabasto",
    "Limpieza o derrames",
    "Cambio de turno o relevo",
    "Otro",
]

# Herramientas de mejora continua sugeridas en los planes de acción
HERRAMIENTAS_MEJORA: list[str] = [
    "5 Porqués",
    "Diagrama de Ishikawa",
    "PEPS / FEFO",
    "5S",
    "Poka-Yoke",
    "Kanban / punto de reorden",
    "Estandarización (SOP)",
    "Capacitación",
    "Negociación con proveedor",
    "Otra",
]

ESTADOS_ACCION: list[str] = ["Pendiente", "En proceso", "Completada", "Cancelada"]


def productos_planos() -> list[dict]:
    """Devuelve el catálogo como lista de diccionarios (una fila por producto)."""
    filas = []
    for depto, productos in DEPARTAMENTOS.items():
        for sku, nombre, unidad, costo in productos:
            filas.append(
                {
                    "sku": sku,
                    "producto": nombre,
                    "departamento": depto,
                    "unidad": unidad,
                    "costo_unitario": costo,
                }
            )
    return filas
