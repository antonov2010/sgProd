"""Datos de EJEMPLO para el tablero gerencial (US-13).

PROVISIONAL: sirve para diseñar la pantalla mientras no existan los
registros reales de captura horaria (US-11 y US-12). Cada registro tiene
la misma forma que tendrá el real, así que al conectar los datos solo hay
que cambiar la función que se llama en views.py.
"""

import random

HORAS = ["07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00"]

# línea -> estación -> (calidad base, meta de piezas por hora)
_LINEAS = {
    "Línea 3": {
        "Corte": (0.98, 40),
        "Costura 1": (0.96, 36),
        "Costura 2": (0.96, 36),
        "Planchado": (0.97, 38),
        "Inspección": (0.99, 40),
        "Empaque": (0.99, 42),
    },
    "Línea 4": {
        "Corte": (0.98, 44),
        "Costura": (0.97, 40),
        "Inspección": (0.99, 44),
        "Empaque": (0.99, 46),
    },
    "Línea 5": {
        "Corte": (0.95, 32),
        "Costura": (0.92, 30),
        "Inspección": (0.96, 34),
        "Empaque": (0.97, 36),
    },
}

# Caídas de calidad para que el tablero cuente una historia:
# (línea, estación) -> (hora desde la que cae, calidad nueva)
_CAIDAS = {
    ("Línea 3", "Costura 2"): (4, 0.66),
}


def registros_ejemplo():
    """Lista de registros hora por hora, con datos reproducibles."""
    azar = random.Random(2026)
    registros = []
    for linea, estaciones in _LINEAS.items():
        for estacion, (calidad, meta) in estaciones.items():
            for i, hora in enumerate(HORAS):
                desde, nueva = _CAIDAS.get((linea, estacion), (99, calidad))
                q = nueva if i >= desde else calidad
                producidas = round(meta * azar.uniform(0.92, 1.04))
                malas = round(producidas * (1 - q))
                rechazadas = round(malas * 0.4)
                retrabajo = malas - rechazadas
                registros.append(
                    {
                        "linea": linea,
                        "estacion": estacion,
                        "hora": hora,
                        "aceptadas": producidas - malas,
                        "rechazadas": rechazadas,
                        "retrabajo": retrabajo,
                        "meta": meta,
                    }
                )
    return registros
