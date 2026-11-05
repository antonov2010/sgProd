"""Reglas de negocio de la matriz de habilidades (RF-1.2).

La lógica vive aquí y no en las vistas para que la pantalla HTML
(``personal:actualizar_nivel_matriz``) y el endpoint REST
(``api:matriz-nivel``) apliquen exactamente las mismas validaciones.
"""

from .models import Empleado, Estacion, NivelHabilidad, SkillMatrix

NIVEL_SIN_ASIGNAR = "Sin nivel"
NIVELES_PERMITIDOS = [*NivelHabilidad.values, NIVEL_SIN_ASIGNAR]


class NivelInvalido(ValueError):
    """El nivel recibido no es uno de los cuatro niveles del catálogo."""


def actualizar_nivel(empleado_id, estacion_id, nivel):
    """Crea, actualiza o elimina el nivel de un empleado en una estación.

    Devuelve el nivel efectivamente guardado. Lanza ``NivelInvalido`` si el
    nivel no pertenece al catálogo, y ``Empleado.DoesNotExist`` /
    ``Estacion.DoesNotExist`` si las llaves foráneas no existen.

    ``Sin nivel`` borra el registro: la matriz se representa con ausencia de
    fila en lugar de con un valor de relleno.
    """
    if nivel not in NIVELES_PERMITIDOS:
        raise NivelInvalido(
            f"Nivel no válido. Debe ser uno de: {', '.join(NIVELES_PERMITIDOS)}"
        )

    empleado = Empleado.objects.get(pk=empleado_id)
    estacion = Estacion.objects.get(pk=estacion_id)

    if nivel == NIVEL_SIN_ASIGNAR:
        SkillMatrix.objects.filter(empleado=empleado, estacion=estacion).delete()
        return NIVEL_SIN_ASIGNAR

    SkillMatrix.objects.update_or_create(
        empleado=empleado,
        estacion=estacion,
        defaults={"nivel": nivel},
    )
    return nivel
