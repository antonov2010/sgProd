"""Cálculo y armado del tablero gerencial At-a-Glance (US-13).

Recibe una lista de registros hora por hora (ver datos_ejemplo.py) y
devuelve un diccionario listo para dibujar con la plantilla
dashboard/_tablero_semaforos.html. No toca la base de datos: así se puede
probar solo y se puede alimentar con datos de ejemplo o reales.

SUPUESTOS PROVISIONALES (confirmar con Rocío y Carlos Eduardo):
- FPY = aceptadas / (aceptadas + rechazadas + retrabajo), como el glosario.
- Tasa de defectos = rechazadas / total de piezas.
- Cumplimiento de meta = piezas aceptadas / meta acumulada.
"""

from .umbrales import ETIQUETAS, UMBRALES, peor, semaforo

_GRAVEDAD_ORDEN = {"bad": 0, "warn": 1, "ok": 2, "none": 3}


def fpy(aceptadas, rechazadas, retrabajo):
    """Porcentaje de piezas buenas a la primera. None si no hay piezas."""
    total = aceptadas + rechazadas + retrabajo
    if total == 0:
        return None
    return round(100 * aceptadas / total, 1)


def tasa_defectos(aceptadas, rechazadas, retrabajo):
    """Porcentaje de piezas rechazadas. None si no hay piezas."""
    total = aceptadas + rechazadas + retrabajo
    if total == 0:
        return None
    return round(100 * rechazadas / total, 1)


def cumplimiento_meta(aceptadas, meta):
    """Porcentaje de la meta alcanzado. None si no hay meta."""
    if meta == 0:
        return None
    return round(100 * aceptadas / meta, 1)


def _sumar(registros):
    suma = {"aceptadas": 0, "rechazadas": 0, "retrabajo": 0, "meta": 0}
    for r in registros:
        for clave in suma:
            suma[clave] += r[clave]
    return suma


def _fpy_de(registros):
    s = _sumar(registros)
    return fpy(s["aceptadas"], s["rechazadas"], s["retrabajo"])


def _texto(valor, decimales=1):
    if valor is None:
        return "—"
    return f"{valor:.{decimales}f} %"


def _objetivo(indicador, umbrales):
    regla = umbrales[indicador]
    signo = "≥" if regla["mejor"] == "alto" else "≤"
    return f"Meta: {signo} {regla['verde']:g} %"


def _agrupar(registros, clave):
    grupos = {}
    for r in registros:
        grupos.setdefault(r[clave], []).append(r)
    return grupos


def _puntos(valores, ancho, alto, margen, ymin, ymax):
    """Convierte valores en coordenadas (x, y) de un SVG."""
    n = len(valores)
    util_x = ancho - 2 * margen
    util_y = alto - 2 * margen
    puntos = []
    for i, v in enumerate(valores):
        x = margen + (util_x * i / (n - 1) if n > 1 else util_x / 2)
        v = ymin if v is None else max(ymin, min(ymax, v))
        y = margen + util_y * (ymax - v) / (ymax - ymin)
        puntos.append((round(x, 1), round(y, 1)))
    return puntos


def _cadena(puntos):
    return " ".join(f"{x},{y}" for x, y in puntos)


def construir_tablero(registros, umbrales=UMBRALES):
    """Arma todo lo que la pantalla necesita a partir de los registros."""
    todas = _sumar(registros)
    f_planta = fpy(todas["aceptadas"], todas["rechazadas"], todas["retrabajo"])
    d_planta = tasa_defectos(
        todas["aceptadas"], todas["rechazadas"], todas["retrabajo"]
    )
    m_planta = cumplimiento_meta(todas["aceptadas"], todas["meta"])

    kpis = []
    for nombre, indicador, valor in (
        ("FPY de planta", "fpy", f_planta),
        ("Cumplimiento de meta", "meta", m_planta),
        ("Tasa de defectos", "defectos", d_planta),
    ):
        estado = semaforo(valor, indicador, umbrales)
        kpis.append(
            {
                "nombre": nombre,
                "valor": _texto(valor),
                "estado": estado,
                "etiqueta": ETIQUETAS[estado],
                "objetivo": _objetivo(indicador, umbrales),
            }
        )

    # Primero se calcula la serie hora por hora de cada línea.
    datos = []
    for nombre, regs in _agrupar(registros, "linea").items():
        estaciones = []
        for est, regs_est in _agrupar(regs, "estacion").items():
            valor = _fpy_de(regs_est)
            estado = semaforo(valor, "fpy", umbrales)
            estaciones.append(
                {
                    "nombre": est,
                    "fpy": _texto(valor),
                    "estado": estado,
                    "etiqueta": ETIQUETAS[estado],
                }
            )
        por_hora = _agrupar(regs, "hora")
        datos.append(
            {
                "nombre": nombre,
                "fpy_num": _fpy_de(regs),
                "estaciones": estaciones,
                "estado": peor(e["estado"] for e in estaciones),
                "horas": list(por_hora),
                "serie": [_fpy_de(por_hora[h]) for h in por_hora],
            }
        )

    todos_los_valores = [
        v for d in datos for v in d["serie"] if v is not None
    ]
    # El eje siempre deja ver los dos umbrales y la caída más baja.
    ymin = umbrales["fpy"]["amarillo"] - 5
    if todos_los_valores:
        ymin = min(ymin, (min(todos_los_valores) // 5) * 5)
    ymin = float(ymin)
    ymax = 100.0

    lineas = []
    for d in datos:
        validos = [v for v in d["serie"] if v is not None]
        # La mini gráfica usa su propia escala para que se note la forma.
        bajo = min(validos, default=ymin) - 1
        alto_s = max(max(validos, default=ymax) + 1, bajo + 4)
        spark = _puntos(d["serie"], 160, 44, 6, bajo, alto_s)
        lineas.append(
            {
                "nombre": d["nombre"],
                "fpy": _texto(d["fpy_num"]),
                "estado": d["estado"],
                "etiqueta": ETIQUETAS[d["estado"]],
                "estaciones": d["estaciones"],
                "spark": _cadena(spark),
            }
        )

    # La gráfica grande muestra la línea con el peor estado (si hay empate,
    # la de menor FPY): es la que el gerente necesita mirar primero.
    tendencia = None
    if datos:
        foco = min(
            datos,
            key=lambda d: (
                _GRAVEDAD_ORDEN[d["estado"]],
                d["fpy_num"] if d["fpy_num"] is not None else 101,
            ),
        )
        horas, serie = foco["horas"], foco["serie"]
        ancho, alto, margen = 640, 240, 48
        pts = _puntos(serie, ancho, alto, margen, ymin, ymax)

        def y_de(valor):
            return _puntos([valor], ancho, alto, margen, ymin, ymax)[0][1]

        tendencia = {
            "titulo": foco["nombre"],
            "ancho": ancho,
            "alto": alto,
            "linea": _cadena(pts),
            "puntos": [
                {
                    "x": x,
                    "y": y,
                    "hora": horas[i],
                    "valor": _texto(serie[i]),
                    "estado": semaforo(serie[i], "fpy", umbrales),
                }
                for i, (x, y) in enumerate(pts)
            ],
            "horas": [{"x": pts[i][0], "texto": h} for i, h in enumerate(horas)],
            "guias": [
                {"y": y_de(v), "texto": f"{v} %"}
                for v in range(int(ymin), 101, 5)
            ],
            "y_verde": y_de(umbrales["fpy"]["verde"]),
            "y_amarillo": y_de(umbrales["fpy"]["amarillo"]),
            "verde": f"{umbrales['fpy']['verde']:g} %",
            "amarillo": f"{umbrales['fpy']['amarillo']:g} %",
            "izq": margen,
            "der": ancho - margen,
            "resumen": ", ".join(
                f"{horas[i]} {_texto(serie[i])}" for i in range(len(horas))
            ),
        }

    return {"kpis": kpis, "lineas": lineas, "tendencia": tendencia}
