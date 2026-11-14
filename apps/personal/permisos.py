"""Reglas de alcance por línea compartidas por el Admin y la API.

La línea del Jefe de Línea se representa con un grupo de Django que se llama
igual que su línea (``Línea 3``, ``Línea 4``, ...). El Admin y el endpoint REST
de la matriz deben aplicar la misma regla; por eso vive aquí y no en una de las
dos vistas.
"""

from .models import Linea


class LineaNoPermitida(ValueError):
    """El usuario no tiene alcance sobre la línea de los datos enviados."""


def lineas_del_usuario(user):
    """Líneas asignadas al Jefe de Línea.

    Un usuario sin grupo de línea no ve datos de planta; el superusuario ve
    todas (el llamador decide si lo restringe).
    """
    if not user.is_authenticated:
        return Linea.objects.none()
    return Linea.objects.filter(nombre__in=user.groups.values_list("name", flat=True))


def linea_autorizada(user, empleado, estacion):
    """Línea sobre la que el usuario puede editar la matriz.

    Devuelve ``None`` para el superusuario (sin restricción) o la línea común
    de empleado y estación cuando pertenece a las líneas del usuario. Lanza
    ``LineaNoPermitida`` si el usuario no tiene grupo de línea o si los datos
    cruzan de línea: empleado y estación deben compartir la misma línea.
    """
    if user.is_superuser:
        return None

    lineas = lineas_del_usuario(user)
    if not lineas.exists():
        raise LineaNoPermitida(
            "No tienes una línea asignada; pide acceso a un administrador."
        )

    if empleado.linea_id != estacion.linea_id:
        raise LineaNoPermitida(
            "El empleado y la estación no pertenecen a la misma línea."
        )

    linea = lineas.filter(pk=empleado.linea_id).first()
    if linea is None:
        raise LineaNoPermitida("No puedes editar la matriz de otra línea.")
    return linea
