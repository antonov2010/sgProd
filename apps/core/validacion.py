"""Validación de cuerpos JSON para las vistas que responden 400 (B-07).

Las pantallas de captura y de la matriz reciben JSON por ``fetch``. Un cuerpo
que no sea un objeto o un id no numérico no debe llegar a ``filter(pk=...)``:
eso producía ``AttributeError``/``ValueError`` y un 500 en lugar de un 400.
"""

import json


class CuerpoInvalido(ValueError):
    """El cuerpo JSON no tiene la forma esperada o trae un campo inválido."""


def objeto_json(cuerpo):
    """Decodifica ``cuerpo`` y exige que la raíz sea un objeto JSON."""
    try:
        datos = json.loads(cuerpo)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise CuerpoInvalido("Cuerpo JSON inválido.") from None
    if not isinstance(datos, dict):
        raise CuerpoInvalido("El cuerpo debe ser un objeto JSON.")
    return datos


def entero_positivo(valor, campo, obligatorio=True):
    """Devuelve ``valor`` como entero positivo o lanza ``CuerpoInvalido``.

    ``None`` y la cadena vacía se consideran ausentes. Sirve para validar los
    ids antes de usarlos en un ``filter(pk=...)``.
    """
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            raise CuerpoInvalido(f"Falta el campo obligatorio «{campo}».")
        return None

    if isinstance(valor, bool):
        raise CuerpoInvalido(f"{campo} debe ser un entero positivo.")
    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, str) and valor.strip().isdigit():
        numero = int(valor.strip())
    else:
        raise CuerpoInvalido(f"{campo} debe ser un entero positivo.")

    if numero <= 0:
        raise CuerpoInvalido(f"{campo} debe ser un entero positivo.")
    return numero
