"""Umbrales vigentes del tablero: base de datos primero, valores por defecto después."""

from .models import UmbralSemaforo
from .umbrales import UMBRALES


def umbrales_actuales():
    """Copia de UMBRALES con los valores configurados en la base de datos."""
    umbrales = {indicador: dict(regla) for indicador, regla in UMBRALES.items()}
    for fila in UmbralSemaforo.objects.all():
        if fila.indicador in umbrales:
            umbrales[fila.indicador]["verde"] = float(fila.verde)
            umbrales[fila.indicador]["amarillo"] = float(fila.amarillo)
    return umbrales
