"""Reglas de negocio de la captura horaria (US-11, RF-2.1).

La lógica vive aquí y no en las vistas (RNF-3): la pantalla de tableta y una
futura ingesta por API (ERP/MES) deben aplicar las mismas validaciones.
"""

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.personal.models import Estacion, Linea, NivelHabilidad, SkillMatrix
from apps.personal.services import obtener_personal_presente

from .models import Asignacion, RegistroCalidadHorario

# Turnos de planta: (primera hora, número de horas). El turno 3 cruza la medianoche.
TURNOS = {
    1: (6, 8),   # 06:00 – 13:59
    2: (14, 8),  # 14:00 – 21:59
    3: (22, 8),  # 22:00 – 05:59
}

# Tope de piezas por estación en una hora; evita errores de dedo (un cero de más).
MAX_PIEZAS_POR_HORA = 9999


class CapturaInvalida(ValueError):
    """Los datos de la captura no cumplen las reglas de RF-2.1."""


@dataclass
class EstacionDelTurno:
    """Una fila de la pantalla de captura: estación, quién la trabaja y su registro."""

    estacion: Estacion
    asignacion: Asignacion | None
    nivel: str | None
    registro: RegistroCalidadHorario | None

    @property
    def requiere_apoyo(self):
        """Mismo criterio que la alerta de US-09: Principiante o sin nivel."""
        return self.asignacion is not None and self.nivel in (None, NivelHabilidad.PRINCIPIANTE)


def horas_del_turno(turno):
    """Horas del reloj (0–23) que forman el turno, en orden."""
    inicio, duracion = TURNOS[turno]
    return [(inicio + i) % 24 for i in range(duracion)]


def turno_de_la_hora(hora):
    """Turno al que pertenece una hora del reloj."""
    for turno in TURNOS:
        if hora in horas_del_turno(turno):
            return turno
    raise CapturaInvalida("La hora debe estar entre 0 y 23.")


def hora_actual():
    return timezone.localtime().hour


def linea_del_jefe(jefe):
    """Línea a cargo del jefe. ``Linea.jefe_linea`` es la fuente de verdad (US-06)."""
    return Linea.objects.filter(jefe_linea=jefe).first() or jefe.linea


def asignaciones_del_turno(linea, turno, asignacion_vigente=None, fecha=None):
    """Asignaciones de la línea para el turno, una por estación.

    Mientras la asignación vigente de RF-1.3 viva en la sesión del jefe, este
    paso la convierte en filas de ``Asignacion``: la captura necesita un
    registro en base de datos al cual colgar las piezas. Si la estación ya tiene
    asignación pero todavía no tiene piezas capturadas, se actualiza al operador
    vigente; si ya tiene piezas, se conserva para no reescribir el historial.

    ``asignacion_vigente`` es el diccionario que guarda la matriz en sesión:
    ``{"<estacion_id>": "<empleado_id>" | None}``.
    """
    fecha = fecha or timezone.localdate()
    asignacion_vigente = asignacion_vigente or {}
    estaciones = list(Estacion.objects.filter(linea=linea).order_by("orden"))
    # Solo personal presente (hook de asistencia RF-1.4): hoy, todo el activo.
    operadores = {e.id: e for e in obtener_personal_presente(linea)}

    existentes = {
        a.estacion_id: a
        for a in Asignacion.objects.filter(
            estacion__in=estaciones, fecha=fecha, turno=turno
        ).select_related("empleado")
    }

    resultado = {}
    with transaction.atomic():
        for estacion in estaciones:
            asignacion = existentes.get(estacion.id)
            vigente_id = asignacion_vigente.get(str(estacion.id))
            operador = operadores.get(int(vigente_id)) if vigente_id else None

            if operador is not None:
                if asignacion is None:
                    asignacion = Asignacion.objects.create(
                        empleado=operador, estacion=estacion, turno=turno
                    )
                elif (
                    asignacion.empleado_id != operador.id
                    and not asignacion.registros_horarios.exists()
                ):
                    asignacion.empleado = operador
                    asignacion.save(update_fields=["empleado"])
            resultado[estacion.id] = asignacion

        niveles = {
            (empleado_id, estacion_id): nivel
            for empleado_id, estacion_id, nivel in SkillMatrix.objects.filter(
                estacion__in=estaciones,
                empleado_id__in=[a.empleado_id for a in resultado.values() if a],
            ).values_list("empleado_id", "estacion_id", "nivel")
        }
        # La alerta de supervisión queda registrada en la asignación (US-09).
        for asignacion in resultado.values():
            if asignacion is None:
                continue
            alerta = niveles.get((asignacion.empleado_id, asignacion.estacion_id)) in (
                None,
                NivelHabilidad.PRINCIPIANTE,
            )
            if asignacion.alerta_supervision != alerta:
                asignacion.alerta_supervision = alerta
                asignacion.save(update_fields=["alerta_supervision"])

    return estaciones, resultado, niveles


def estaciones_para_capturar(linea, turno, hora, asignacion_vigente=None, fecha=None):
    """Filas de la pantalla de captura para una hora del turno."""
    estaciones, asignaciones, niveles = asignaciones_del_turno(
        linea, turno, asignacion_vigente, fecha
    )
    registros = {
        r.asignacion_id: r
        for r in RegistroCalidadHorario.objects.filter(
            asignacion__in=[a for a in asignaciones.values() if a], hora=hora
        )
    }
    filas = []
    for estacion in estaciones:
        asignacion = asignaciones[estacion.id]
        filas.append(
            EstacionDelTurno(
                estacion=estacion,
                asignacion=asignacion,
                nivel=niveles.get((asignacion.empleado_id, estacion.id)) if asignacion else None,
                registro=registros.get(asignacion.id) if asignacion else None,
            )
        )
    return filas


def historial_del_turno(linea, turno, fecha=None):
    """Registros ya guardados del turno, de la hora más reciente a la más antigua."""
    fecha = fecha or timezone.localdate()
    orden_hora = {h: i for i, h in enumerate(horas_del_turno(turno))}
    registros = list(
        RegistroCalidadHorario.objects.filter(
            asignacion__estacion__linea=linea,
            asignacion__fecha=fecha,
            asignacion__turno=turno,
        ).select_related("asignacion__estacion", "asignacion__empleado")
    )
    registros.sort(
        key=lambda r: (-orden_hora.get(r.hora, -1), r.asignacion.estacion.orden)
    )
    return registros


def _piezas(valor, campo):
    try:
        piezas = int(valor)
    except (TypeError, ValueError):
        raise CapturaInvalida(f"{campo}: escribe un número entero.") from None
    if piezas < 0:
        raise CapturaInvalida(f"{campo}: no puede ser negativo.")
    if piezas > MAX_PIEZAS_POR_HORA:
        raise CapturaInvalida(f"{campo}: máximo {MAX_PIEZAS_POR_HORA} piezas por hora.")
    return piezas


def registrar_captura(linea, asignacion_id, hora, aceptadas, rechazadas, retrabajo, fecha=None):
    """Guarda (o corrige) las piezas de una estación en una hora del turno.

    Un mismo par asignación + hora tiene un solo registro: volver a guardar la
    misma hora corrige los valores en lugar de duplicarlos.

    Lanza ``CapturaInvalida`` si los datos no son válidos o la asignación no
    pertenece a la línea del jefe ni al día en curso.
    """
    fecha = fecha or timezone.localdate()
    valores = {
        "piezas_aceptadas": _piezas(aceptadas, "Aceptadas"),
        "piezas_rechazadas": _piezas(rechazadas, "Rechazadas"),
        "piezas_retrabajo": _piezas(retrabajo, "Retrabajo"),
    }
    try:
        hora = int(hora)
    except (TypeError, ValueError):
        raise CapturaInvalida("Hora no válida.") from None

    asignacion = (
        Asignacion.objects.filter(pk=asignacion_id, estacion__linea=linea, fecha=fecha)
        .select_related("estacion", "empleado")
        .first()
    )
    if asignacion is None:
        raise CapturaInvalida("La estación no pertenece a tu línea o a este turno.")
    if hora not in horas_del_turno(asignacion.turno):
        raise CapturaInvalida("La hora no pertenece a este turno.")

    with transaction.atomic():
        registro = (
            RegistroCalidadHorario.objects.select_for_update()
            .filter(asignacion=asignacion, hora=hora)
            .first()
        )
        creado = registro is None
        if creado:
            registro = RegistroCalidadHorario.objects.create(
                asignacion=asignacion, hora=hora, **valores
            )
        else:
            for campo, valor in valores.items():
                setattr(registro, campo, valor)
            registro.save(update_fields=list(valores))
    return registro, creado
