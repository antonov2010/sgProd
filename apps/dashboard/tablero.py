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

from .kpis import (
    calcular_fpy as fpy,
    calcular_tasa_defectos as tasa_defectos,
    desglosar_kpis,
)
from .umbrales import ETIQUETAS, UMBRALES, peor, semaforo

_GRAVEDAD_ORDEN = {"bad": 0, "warn": 1, "ok": 2, "none": 3}


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


def _grafica(horas, serie, ymin, ymax, umbrales):
    """Geometría de la gráfica grande de una línea (SVG)."""
    ancho, alto, margen = 640, 240, 48
    pts = _puntos(serie, ancho, alto, margen, ymin, ymax)

    def y_de(valor):
        return _puntos([valor], ancho, alto, margen, ymin, ymax)[0][1]

    return {
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
            {"y": y_de(v), "texto": f"{v} %"} for v in range(int(ymin), 101, 5)
        ],
        "y_verde": y_de(umbrales["fpy"]["verde"]),
        "y_amarillo": y_de(umbrales["fpy"]["amarillo"]),
        "verde": f"{umbrales['fpy']['verde']:g} %",
        "amarillo": f"{umbrales['fpy']['amarillo']:g} %",
        "izq": margen,
        "der": ancho - margen,
        "resumen": ", ".join(f"{horas[i]} {_texto(serie[i])}" for i in range(len(horas))),
    }


def _personal_linea(info, visibles=6):
    """Quién está en la línea; solo se muestran los primeros nombres."""
    if not info:
        return {"jefe": "", "total": 0, "visibles": [], "mas": 0}
    operadores = list(info.get("operadores", []))
    return {
        "jefe": info.get("jefe", ""),
        "total": len(operadores),
        "visibles": operadores[:visibles],
        "mas": max(0, len(operadores) - visibles),
    }


def _piezas_por_hora(registros, umbrales):
    """Piezas buenas por hora (promedio por estación) contra la meta."""
    horas = {r["hora"] for r in registros}
    estaciones = {r["estacion"] for r in registros}
    base = len(horas) * len(estaciones)
    if base == 0:
        return None
    s = _sumar(registros)
    cumplimiento = cumplimiento_meta(s["aceptadas"], s["meta"])
    estado = semaforo(cumplimiento, "meta", umbrales)
    tope = 120.0  # la barra llega hasta 120 % de la meta
    ancho = 0 if cumplimiento is None else min(cumplimiento, tope) / tope * 100
    return {
        "valor": f"{s['aceptadas'] / base:.1f}",
        "meta": f"{s['meta'] / base:.1f}",
        "cumplimiento": _texto(cumplimiento),
        "estado": estado,
        "etiqueta": ETIQUETAS[estado],
        "ancho": f"{ancho:.1f}",
        "marca": f"{100 / tope * 100:.1f}",
    }


def _defectos_por_empleado(registros, umbrales, limite=6):
    """Empleados con mayor tasa de rechazo (solo si el registro trae empleado)."""
    grupos = {}
    for r in registros:
        if r.get("empleado"):
            clave = (r["empleado"], r["linea"], r["estacion"])
            grupos.setdefault(clave, []).append(r)
    filas = []
    for (nombre, linea, estacion), regs in grupos.items():
        s = _sumar(regs)
        tasa = tasa_defectos(s["aceptadas"], s["rechazadas"], s["retrabajo"])
        filas.append((tasa if tasa is not None else -1, nombre, linea, estacion, s))
    filas.sort(key=lambda f: (-f[0], f[1]))
    maximo = max((f[0] for f in filas), default=0) or 1
    resultado = []
    for tasa, nombre, linea, estacion, s in filas[:limite]:
        valor = None if tasa < 0 else tasa
        estado = semaforo(valor, "defectos", umbrales)
        resultado.append(
            {
                "nombre": nombre,
                "donde": f"{linea} · {estacion}",
                "tasa": _texto(valor),
                "rechazadas": s["rechazadas"],
                "estado": estado,
                "etiqueta": ETIQUETAS[estado],
                "ancho": f"{max(valor or 0, 0) / maximo * 100:.1f}",
            }
        )
    return resultado


def construir_tablero(registros, personal=None, umbrales=UMBRALES):
    """Arma todo lo que la pantalla necesita a partir de los registros.

    personal: dict opcional {línea: {"jefe": str, "operadores": [str]}}.
    """
    personal = personal or {}
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
                "regs": regs,
                "estado": peor(e["estado"] for e in estaciones),
                "horas": list(por_hora),
                "serie": [_fpy_de(por_hora[h]) for h in por_hora],
            }
        )

    valores = [v for d in datos for v in d["serie"] if v is not None]
    # El eje siempre deja ver los dos umbrales y la caída más baja.
    ymin = umbrales["fpy"]["amarillo"] - 5
    if valores:
        ymin = min(ymin, (min(valores) // 5) * 5)
    ymin = float(ymin)
    ymax = 100.0

    lineas = []
    for i, d in enumerate(datos, start=1):
        validos = [v for v in d["serie"] if v is not None]
        # La mini gráfica usa su propia escala para que se note la forma.
        bajo = min(validos, default=ymin) - 1
        alto_s = max(max(validos, default=ymax) + 1, bajo + 4)
        lineas.append(
            {
                "id": f"l{i}",
                "nombre": d["nombre"],
                "fpy": _texto(d["fpy_num"]),
                "fpy_num": d["fpy_num"],
                "estado": d["estado"],
                "etiqueta": ETIQUETAS[d["estado"]],
                "estaciones": d["estaciones"],
                "spark": _cadena(_puntos(d["serie"], 160, 44, 6, bajo, alto_s)),
                "personal": _personal_linea(personal.get(d["nombre"])),
                "piezas": _piezas_por_hora(d["regs"], umbrales),
                "grafica": _grafica(d["horas"], d["serie"], ymin, ymax, umbrales),
            }
        )

    # Al abrir, la gráfica grande es la de la línea con peor estado
    # (si hay empate, la de menor FPY): es la que se debe mirar primero.
    activa = None
    if lineas:
        foco = min(
            lineas,
            key=lambda x: (
                _GRAVEDAD_ORDEN[x["estado"]],
                x["fpy_num"] if x["fpy_num"] is not None else 101,
            ),
        )
        activa = foco["id"]

    return {
        "kpis": kpis,
        "lineas": lineas,
        "activa": activa,
        "empleados": _defectos_por_empleado(registros, umbrales),
        "por_estacion": desglosar_kpis(registros, "estacion"),
        "por_turno": desglosar_kpis(registros, "turno"),
    }
