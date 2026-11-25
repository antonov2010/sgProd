"""Validación de cuerpos JSON para las vistas que responden 400 (B-07).

Las pantallas de captura y de la matriz reciben JSON por ``fetch``. Un cuerpo
que no sea un objeto o un id no numérico no debe llegar a ``filter(pk=...)``:
eso producía ``AttributeError``/``ValueError`` y un 500 en lugar de un 400.
"""

import json
import math
import re

# Solo dígitos ASCII: ``str.isdigit()`` acepta "²" o "³", que ``int()`` rechaza.
_DIGITOS = re.compile(r"[0-9]+")


class CuerpoInvalido(ValueError):
    """El cuerpo JSON no tiene la forma esperada o trae un campo inválido."""


def _numero_no_finito(_texto):
    raise CuerpoInvalido("El cuerpo trae un número no válido (NaN o Infinity).")


def _decimal_finito(texto):
    """``json.loads`` convierte ``1e400`` en infinito; eso no es un dato de planta."""
    numero = float(texto)
    if not math.isfinite(numero):
        _numero_no_finito(texto)
    return numero


def objeto_json(cuerpo):
    """Decodifica ``cuerpo`` y exige que la raíz sea un objeto JSON.

    Rechaza también ``NaN``, ``Infinity`` y decimales que desbordan: Python los
    acepta como JSON, pero ``int(inf)`` lanza ``OverflowError`` y daba un 500
    (SGPRO-35).
    """
    try:
        datos = json.loads(
            cuerpo, parse_constant=_numero_no_finito, parse_float=_decimal_finito
        )
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
    elif isinstance(valor, str) and _DIGITOS.fullmatch(valor.strip()):
        numero = int(valor.strip())
    else:
        raise CuerpoInvalido(f"{campo} debe ser un entero positivo.")

    if numero <= 0:
        raise CuerpoInvalido(f"{campo} debe ser un entero positivo.")
    return numero
