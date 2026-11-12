"""Umbrales de los semáforos del tablero (US-13).

PROVISIONAL: estos valores son de ejemplo. Rocío debe definir los reales
(supuesto 4 del alcance: los umbrales son configuración, no constantes
repartidas por el código). Para cambiar un color del tablero basta con
editar los números de este archivo, sin tocar ninguna otra parte.

"mejor": "alto" significa que un valor mayor es mejor (FPY, cumplimiento).
"mejor": "bajo" significa que un valor menor es mejor (tasa de defectos).
"""

UMBRALES = {
    "fpy": {"verde": 95.0, "amarillo": 90.0, "mejor": "alto"},
    "meta": {"verde": 100.0, "amarillo": 85.0, "mejor": "alto"},
    "defectos": {"verde": 2.0, "amarillo": 5.0, "mejor": "bajo"},
}

ETIQUETAS = {
    "ok": "En meta",
    "warn": "Atención",
    "bad": "Crítico",
    "none": "Sin datos",
}

_GRAVEDAD = {"bad": 0, "warn": 1, "ok": 2, "none": 3}


def semaforo(valor, indicador, umbrales=UMBRALES):
    """Devuelve 'ok', 'warn', 'bad' o 'none' según el valor y el umbral."""
    if valor is None:
        return "none"
    regla = umbrales[indicador]
    verde, amarillo = regla["verde"], regla["amarillo"]
    if regla["mejor"] == "alto":
        if valor >= verde:
            return "ok"
        return "warn" if valor >= amarillo else "bad"
    if valor <= verde:
        return "ok"
    return "warn" if valor <= amarillo else "bad"


def peor(estados):
    """Devuelve el estado más grave de una lista (para resumir una línea)."""
    estados = list(estados)
    if not estados:
        return "none"
    return min(estados, key=lambda e: _GRAVEDAD[e])
