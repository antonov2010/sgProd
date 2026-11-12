"""Datos REALES para el tablero gerencial (US-13).

Lee la base de datos y devuelve exactamente la misma forma que
datos_ejemplo.py, así construir_tablero() no cambia.

Modelos que usa (solo lectura, no se toca ninguno):
- personal.Linea / Empleado / Estacion
- calidad.Asignacion y RegistroCalidadHorario (piezas por hora)
- dashboard.MetaEstacion (meta de piezas por hora de cada estación)
"""

from apps.calidad.models import RegistroCalidadHorario
from apps.personal.models import Empleado, Linea

META_POR_DEFECTO = 100  # igual que MetaEstacion.piezas_por_hora_meta


def _etiqueta_hora(hora):
    return f"Hora {hora}"


def registros_reales(fecha=None):
    """Registros hora por hora de UN día (por defecto el más reciente).

    Devuelve [] si todavía no hay captura. Cada registro:
    linea, estacion, empleado, hora, aceptadas, rechazadas, retrabajo, meta.
    """
    base = RegistroCalidadHorario.objects.all()
    if fecha is None:
        ultimo = base.order_by("-asignacion__fecha").first()
        if ultimo is None:
            return []
        fecha = ultimo.asignacion.fecha
    consulta = (
        base.filter(asignacion__fecha=fecha)
        .select_related(
            "asignacion__empleado",
            "asignacion__estacion__linea",
            "asignacion__estacion__meta",
        )
        .order_by("hora", "asignacion__estacion__linea__nombre", "asignacion__estacion__orden")
    )
    registros = []
    for r in consulta:
        estacion = r.asignacion.estacion
        meta_obj = getattr(estacion, "meta", None)
        registros.append(
            {
                "linea": estacion.linea.nombre,
                "estacion": estacion.nombre,
                "empleado": r.asignacion.empleado.nombre,
                "hora": _etiqueta_hora(r.hora),
                "aceptadas": r.piezas_aceptadas,
                "rechazadas": r.piezas_rechazadas,
                "retrabajo": r.piezas_retrabajo,
                "meta": meta_obj.piezas_por_hora_meta if meta_obj else META_POR_DEFECTO,
            }
        )
    return registros


def personal_real():
    """{línea: {"jefe": nombre, "operadores": [nombres]}} con gente activa."""
    personal = {}
    for linea in Linea.objects.select_related("jefe_linea").order_by("nombre"):
        operadores = (
            Empleado.objects.filter(linea=linea, activo=True, rol__tipo_rol="operador")
            .order_by("nombre")
            .values_list("nombre", flat=True)
        )
        personal[linea.nombre] = {
            "jefe": linea.jefe_linea.nombre if linea.jefe_linea else "",
            "operadores": list(operadores),
        }
    return personal
