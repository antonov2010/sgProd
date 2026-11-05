"""Datos de EJEMPLO para el tablero gerencial (US-13).

PROVISIONAL: sirve para diseñar la pantalla mientras no se conecten los
datos reales. Cada registro tiene la misma forma que tendrá el real, así
que al conectar la base de datos solo hay que cambiar las dos funciones
que se llaman en views.py:

- registros_ejemplo(): piezas aceptadas, rechazadas y retrabajo por hora.
- personal_ejemplo(): quién está en cada línea (Jefe y operadores).
"""

import random

HORAS = ["07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00"]

# estación -> meta de piezas por hora (las estaciones de la matriz de Mariana)
_ESTACIONES = {
    "Corte": 40,
    "Crimpado": 38,
    "Soldadura": 36,
    "Ensamble": 36,
    "Prueba eléctrica": 34,
    "Inspección visual": 40,
    "Empaque": 42,
    "Etiquetado": 44,
}

# calidad base de cada línea (proporción de piezas buenas)
_CALIDAD_LINEA = {
    "Línea 1": 0.985,
    "Línea 2": 0.980,
    "Línea 3": 0.975,
    "Línea 4": 0.990,
    "Línea 5": 0.975,
    "Línea 6": 0.975,
    "Línea 7": 0.985,
}

# ritmo de producción de cada línea (1.0 = cumple justo la meta)
_RITMO = {
    "Línea 1": 1.03,
    "Línea 2": 1.02,
    "Línea 3": 0.97,
    "Línea 4": 1.05,
    "Línea 5": 0.95,
    "Línea 6": 0.99,
    "Línea 7": 1.03,
}

# Historias para que el tablero se vea con vida:
# (línea, estación) -> (hora desde la que aplica, calidad nueva)
_CAIDAS = {
    ("Línea 3", "Soldadura"): (4, 0.62),  # cae a media mañana: rojo
    ("Línea 5", "Crimpado"): (0, 0.93),  # siempre un poco bajo: amarillo
    ("Línea 6", "Ensamble"): (5, 0.80),  # cae al final del turno: amarillo
}

_NOMBRES = [
    "Ana", "Luis", "Carmen", "Jorge", "Rosa", "Miguel", "Elena", "Pablo",
    "Sofía", "Diego", "Laura", "Andrés", "Marisol", "Raúl", "Paola", "Hugo",
    "Daniela", "Iván", "Verónica", "Óscar",
]
_APELLIDOS = [
    "Ramírez", "Martínez", "Soto", "Pérez", "Díaz", "Torres", "Vargas",
    "Núñez", "Ibarra", "Flores", "Reyes", "Castro", "Ortiz", "Salas",
    "Méndez", "Herrera", "Navarro", "Rojas", "Campos", "Luna",
]


def registros_ejemplo():
    """Lista de registros hora por hora, con datos reproducibles.

    Cada registro incluye el empleado que operó la estación ("empleado"),
    para poder calcular la tasa de defectos por empleado.
    """
    azar = random.Random(2026)
    personal = personal_ejemplo()
    registros = []
    for linea, calidad in _CALIDAD_LINEA.items():
        operadores = personal[linea]["operadores"]
        for n, (estacion, meta) in enumerate(_ESTACIONES.items()):
            empleado = operadores[n % len(operadores)]
            for i, hora in enumerate(HORAS):
                desde, nueva = _CAIDAS.get((linea, estacion), (99, calidad))
                q = nueva if i >= desde else calidad
                ritmo = _RITMO[linea]
                producidas = round(meta * azar.uniform(ritmo - 0.03, ritmo + 0.03))
                malas = round(producidas * (1 - q))
                rechazadas = round(malas * 0.4)
                registros.append(
                    {
                        "linea": linea,
                        "estacion": estacion,
                        "empleado": empleado,
                        "hora": hora,
                        "aceptadas": producidas - malas,
                        "rechazadas": rechazadas,
                        "retrabajo": malas - rechazadas,
                        "meta": meta,
                    }
                )
    return registros


def personal_ejemplo():
    """Quién está en cada línea: un Jefe y varios operadores."""
    azar = random.Random(11)
    usados = set()

    def nombre():
        while True:
            n = f"{azar.choice(_NOMBRES)} {azar.choice(_APELLIDOS)}"
            if n not in usados:
                usados.add(n)
                return n

    return {
        linea: {
            "jefe": nombre(),
            "operadores": [nombre() for _ in range(azar.randint(14, 20))],
        }
        for linea in _CALIDAD_LINEA
    }
