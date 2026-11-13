"""Lógica de negocio para elegibles a bono por cero defectos (US-15 / RF-3.3)."""

from apps.calidad.models import RegistroCalidadHorario

from .kpis import calcular_fpy, calcular_tasa_defectos
from .models import ConfiguracionBono


def obtener_configuracion_bono():
    """Obtiene la regla activa de periodo o devuelve una instancia por defecto (últimos 7 días)."""
    config = ConfiguracionBono.objects.filter(activo=True).order_by("-id").first()
    if config is None:
        config = ConfiguracionBono(tipo_periodo="dias", dias_evaluacion=7, activo=True)
    return config


def calcular_elegibles_bono(fecha_inicio=None, fecha_fin=None):
    """Calcula los operadores con 0 defectos y producción > 0 en el periodo configurado.

    Devuelve un diccionario con:
    - periodo: {"inicio": date, "fin": date, "tipo": str}
    - elegibles: lista de dicts con datos del operador, totales y sus registros de respaldo.
    """
    config = obtener_configuracion_bono()
    if fecha_inicio is None or fecha_fin is None:
        fecha_inicio, fecha_fin = config.obtener_rango()

    qs = (
        RegistroCalidadHorario.objects.select_related(
            "asignacion__empleado",
            "asignacion__estacion__linea",
        )
        .filter(
            asignacion__fecha__range=(fecha_inicio, fecha_fin),
            asignacion__empleado__activo=True,
        )
        .order_by("asignacion__fecha", "hora")
    )

    por_empleado = {}
    for reg in qs:
        emp = reg.asignacion.empleado
        grupo = por_empleado.setdefault(
            emp.id,
            {
                "empleado_id": emp.id,
                "numero_empleado": emp.numero_empleado,
                "nombre": emp.nombre,
                "aceptadas": 0,
                "rechazadas": 0,
                "retrabajo": 0,
                "registros": [],
            },
        )
        grupo["aceptadas"] += reg.piezas_aceptadas
        grupo["rechazadas"] += reg.piezas_rechazadas
        grupo["retrabajo"] += reg.piezas_retrabajo
        grupo["registros"].append(
            {
                "id": reg.id,
                "fecha": reg.asignacion.fecha,
                "turno": reg.asignacion.turno,
                "linea": reg.asignacion.estacion.linea.nombre,
                "estacion": reg.asignacion.estacion.nombre,
                "hora": reg.hora,
                "aceptadas": reg.piezas_aceptadas,
                "rechazadas": reg.piezas_rechazadas,
                "retrabajo": reg.piezas_retrabajo,
            }
        )

    elegibles = []
    for datos in por_empleado.values():
        total_piezas = datos["aceptadas"] + datos["rechazadas"] + datos["retrabajo"]
        # Criterios US-15: tuvo producción en el periodo y cero piezas rechazadas
        if total_piezas > 0 and datos["rechazadas"] == 0:
            datos["total_piezas"] = total_piezas
            datos["total_registros"] = len(datos["registros"])
            datos["fpy"] = calcular_fpy(
                datos["aceptadas"], datos["rechazadas"], datos["retrabajo"]
            )
            datos["tasa_defectos"] = calcular_tasa_defectos(
                datos["aceptadas"], datos["rechazadas"], datos["retrabajo"]
            )
            elegibles.append(datos)

    elegibles.sort(key=lambda x: (-x["aceptadas"], x["nombre"]))

    return {
        "periodo": {
            "inicio": fecha_inicio,
            "fin": fecha_fin,
            "tipo": config.get_tipo_periodo_display(),
        },
        "elegibles": elegibles,
    }