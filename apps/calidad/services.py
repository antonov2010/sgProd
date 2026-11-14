"""Reglas de negocio de la captura horaria (US-11, RF-2.1, RF-2.2).

La lógica vive aquí y no en las vistas (RNF-3): la pantalla de tableta y una
futura ingesta por API (ERP/MES) deben aplicar las mismas validaciones.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.personal.models import Estacion, Linea, NivelHabilidad, SkillMatrix
from apps.personal.services import obtener_personal_presente

from .models import Asignacion, CatalogoDefecto, DetalleDefecto, RegistroCalidadHorario

# Turnos de planta: (primera hora, número de horas). El turno 3 cruza la medianoche.
TURNOS = {
    1: (6, 8),   # 06:00 – 13:59
    2: (14, 8),  # 14:00 – 21:59
    3: (22, 8),  # 22:00 – 05:59
}

# Tope de piezas por estación en una hora; evita errores de dedo (un cero de más).
MAX_PIEZAS_POR_HORA = 9999


class CapturaInvalida(ValueError):
    """Los datos de la captura no cumplen las reglas de RF-2.1 / RF-2.2."""


@dataclass
class EstacionDelTurno:
    """Una fila de la pantalla de captura: estación, quién la trabaja y su registro."""

    estacion: Estacion
    asignacion: Asignacion | None
    nivel: str | None
    registro: RegistroCalidadHorario | None
    defecto_id: int | None = None

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


def fecha_de_la_guardia(turno, fecha=None):
    """Fecha de la guardia a la que pertenece un turno.

    El turno 3 (22:00–05:59) pertenece al día en que inicia la guardia: de
    madrugada (00:00–05:59) la guardia en curso es la que arrancó ayer a las
    22:00, y sus 8 horas viven en la misma ``Asignacion``. En cualquier otro
    momento la fecha de planta es la de hoy. Si ``fecha`` llega explícita (una
    corrección histórica), se respeta tal cual.
    """
    if fecha is not None:
        return fecha
    if turno == 3 and hora_actual() <= 5:
        return timezone.localdate() - timedelta(days=1)
    return timezone.localdate()


def linea_del_jefe(jefe):
    """Línea a cargo del jefe. ``Linea.jefe_linea`` es la fuente de verdad (US-06)."""
    return Linea.objects.filter(jefe_linea=jefe).first() or jefe.linea


def _niveles_de(estaciones, asignaciones):
    """Nivel de habilidad de cada operador asignado en su estación."""
    return {
        (empleado_id, estacion_id): nivel
        for empleado_id, estacion_id, nivel in SkillMatrix.objects.filter(
            estacion__in=estaciones,
            empleado_id__in=[a.empleado_id for a in asignaciones.values() if a],
        ).values_list("empleado_id", "estacion_id", "nivel")
    }


def _alerta_supervision(niveles, asignacion):
    """US-09: alerta cuando el operador es Principiante o no tiene nivel."""
    return niveles.get((asignacion.empleado_id, asignacion.estacion_id)) in (
        None,
        NivelHabilidad.PRINCIPIANTE,
    )


def guardar_asignacion_vigente(linea, asignacion_vigente, fecha=None, turno=None):
    """Persiste la asignación vigente de RF-1.3 como ``Asignacion`` del turno.

    US-08 exige que la asignación aceptada quede registrada. La matriz llama a
    esta función al confirmar la propuesta; la captura ya no escribe en base de
    datos al abrirse. Reglas:

    * las filas del turno se leen y bloquean dentro de la transacción, y se
      crean con ``get_or_create``: confirmar dos veces no duplica estaciones;
    * una estación que se envía sin operador queda descubierta: se borra su
      asignación si aún no tiene piezas; si ya las tiene, se conserva;
    * una persona se asigna una sola vez por turno y gana la primera estación
      por orden (la que el jefe vio primero y suele ser su cambio manual). Si
      una estación posterior vuelve a traerla, esa estación queda descubierta y
      se avisa; no se mueve ni se borra la asignación de otra estación para
      hacerle espacio;
    * una estación con piezas capturadas conserva a su operador y se avisa;
    * un operador dado de baja no se asigna (RF-1.4).

    ``asignacion_vigente``: ``{"<estacion_id>": "<empleado_id>" | None}``.

    Devuelve ``(estaciones, resultado, niveles, avisos)``; ``avisos`` son
    mensajes en español para el jefe sobre estaciones conservadas o conflictos.
    """
    turno = turno or turno_de_la_hora(hora_actual())
    fecha = fecha_de_la_guardia(turno, fecha)
    asignacion_vigente = asignacion_vigente or {}
    estaciones = list(Estacion.objects.filter(linea=linea).order_by("orden"))
    operadores = {e.id: e for e in obtener_personal_presente(linea)}

    resultado = {}
    avisos = []
    with transaction.atomic():
        # La lectura va dentro de la transacción y con bloqueo para que dos
        # confirmaciones simultáneas no creen filas duplicadas.
        existentes = {
            asignacion.estacion_id: asignacion
            for asignacion in Asignacion.objects.select_for_update()
            .filter(estacion__in=estaciones, fecha=fecha, turno=turno)
            .select_related("empleado")
            .order_by("id")
        }
        # Ganadores del turno: ``empleado_id -> asignación`` de la primera
        # estación por orden. Solo crece; una estación posterior nunca mueve ni
        # borra la asignación de otra estación para "hacer espacio".
        ganadores = {}

        for estacion in estaciones:
            asignacion = existentes.get(estacion.id)
            vigente_id = asignacion_vigente.get(str(estacion.id))
            operador = operadores.get(int(vigente_id)) if vigente_id else None

            if operador is None:
                # Limpiar la estación: solo se borra si no hay piezas capturadas.
                if asignacion is not None:
                    if asignacion.registros_horarios.exists():
                        avisos.append(
                            f"{estacion.nombre}: ya tenía piezas capturadas; se "
                            f"conserva a {asignacion.empleado.nombre}."
                        )
                        ganadores.setdefault(asignacion.empleado_id, asignacion)
                        resultado[estacion.id] = asignacion
                        continue
                    asignacion.delete()
                    existentes.pop(estacion.id, None)
                    asignacion = None
                resultado[estacion.id] = None
                continue

            # Una estación con piezas capturadas conserva a su operador, aunque
            # el formulario proponga otro: no se reescribe su historial.
            if asignacion is not None and asignacion.registros_horarios.exists():
                anterior = ganadores.get(asignacion.empleado_id)
                if asignacion.empleado_id == operador.id and anterior is not None:
                    avisos.append(
                        f"{estacion.nombre}: ya tenía piezas capturadas; se "
                        f"conserva a {operador.nombre}, que ya está asignada a "
                        f"{anterior.estacion.nombre}."
                    )
                elif asignacion.empleado_id != operador.id and anterior is not None:
                    avisos.append(
                        f"{estacion.nombre}: ya tenía piezas capturadas; se "
                        f"conserva a {asignacion.empleado.nombre}, que ya está "
                        f"asignado a {anterior.estacion.nombre}, y no se asigna a "
                        f"{operador.nombre}."
                    )
                elif asignacion.empleado_id != operador.id:
                    avisos.append(
                        f"{estacion.nombre}: ya tenía piezas capturadas; se conserva "
                        f"a {asignacion.empleado.nombre} y no se asigna a "
                        f"{operador.nombre}."
                    )
                ganadores.setdefault(asignacion.empleado_id, asignacion)
                resultado[estacion.id] = asignacion
                continue

            # Gana la primera estación por orden: si una estación posterior trae
            # a alguien ya asignado, queda descubierta y se avisa al jefe.
            anterior = ganadores.get(operador.id)
            if anterior is not None:
                if asignacion is not None:
                    asignacion.delete()
                    existentes.pop(estacion.id, None)
                avisos.append(
                    f"{estacion.nombre}: {operador.nombre} ya está asignada a "
                    f"{anterior.estacion.nombre}; la estación queda descubierta."
                )
                resultado[estacion.id] = None
                continue

            if asignacion is None:
                asignacion, _ = Asignacion.objects.get_or_create(
                    estacion=estacion,
                    fecha=fecha,
                    turno=turno,
                    defaults={"empleado": operador},
                )
                existentes[estacion.id] = asignacion
            elif asignacion.empleado_id != operador.id:
                asignacion.empleado = operador
                asignacion.save(update_fields=["empleado"])

            ganadores[operador.id] = asignacion
            resultado[estacion.id] = asignacion

        niveles = _niveles_de(estaciones, resultado)
        for asignacion in resultado.values():
            if asignacion is None:
                continue
            alerta = _alerta_supervision(niveles, asignacion)
            if asignacion.alerta_supervision != alerta:
                asignacion.alerta_supervision = alerta
                asignacion.save(update_fields=["alerta_supervision"])

    return estaciones, resultado, niveles, avisos


def asignaciones_del_turno(linea, turno, fecha=None):
    """Asignaciones ya registradas de la línea para el turno (solo lectura).

    La asignación vigente se guarda al confirmarla en la matriz (US-08); esta
    consulta no crea ni modifica filas.
    """
    fecha = fecha_de_la_guardia(turno, fecha)
    estaciones = list(Estacion.objects.filter(linea=linea).order_by("orden"))
    resultado = {
        a.estacion_id: a
        for a in Asignacion.objects.filter(
            estacion__in=estaciones,
            fecha=fecha,
            turno=turno,
            empleado__activo=True,
        ).select_related("empleado")
    }
    return estaciones, resultado, _niveles_de(estaciones, resultado)


def estaciones_para_capturar(linea, turno, hora, fecha=None):
    """Filas de la pantalla de captura para una hora del turno."""
    fecha = fecha_de_la_guardia(turno, fecha)
    estaciones, asignaciones, niveles = asignaciones_del_turno(linea, turno, fecha)
    registros = {
        r.asignacion_id: r
        for r in RegistroCalidadHorario.objects.filter(
            asignacion__in=[a for a in asignaciones.values() if a], hora=hora
        ).prefetch_related("defectos")
    }
    filas = []
    for estacion in estaciones:
        asignacion = asignaciones.get(estacion.id)
        registro = registros.get(asignacion.id) if asignacion else None
        primer_defecto = registro.defectos.first() if registro else None
        filas.append(
            EstacionDelTurno(
                estacion=estacion,
                asignacion=asignacion,
                nivel=niveles.get((asignacion.empleado_id, estacion.id)) if asignacion else None,
                registro=registro,
                defecto_id=primer_defecto.defecto_id if primer_defecto else None,
            )
        )
    return filas


def historial_del_turno(linea, turno, fecha=None):
    """Registros ya guardados del turno, de la hora más reciente a la más antigua."""
    fecha = fecha_de_la_guardia(turno, fecha)
    orden_hora = {h: i for i, h in enumerate(horas_del_turno(turno))}
    registros = list(
        RegistroCalidadHorario.objects.filter(
            asignacion__estacion__linea=linea,
            asignacion__fecha=fecha,
            asignacion__turno=turno,
        )
        .select_related("asignacion__estacion", "asignacion__empleado")
        .prefetch_related("defectos__defecto")
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


def registrar_captura(
    linea, asignacion_id, hora, aceptadas, rechazadas, retrabajo, defecto_id=None, fecha=None
):
    """Guarda (o corrige) las piezas de una estación en una hora del turno."""
    # El turno en curso se resuelve con el reloj: de madrugada el turno 3 sigue
    # siendo el de la guardia que empezó ayer (B-05).
    turno_actual = turno_de_la_hora(hora_actual())
    fecha_guardia = fecha_de_la_guardia(turno_actual)
    fecha = fecha or fecha_guardia
    valores = {
        "piezas_aceptadas": _piezas(aceptadas, "Aceptadas"),
        "piezas_rechazadas": _piezas(rechazadas, "Rechazadas"),
        "piezas_retrabajo": _piezas(retrabajo, "Retrabajo"),
    }
    try:
        hora = int(hora)
    except (TypeError, ValueError):
        raise CapturaInvalida("Hora no válida.") from None

    # Validación RF-2.2: motivo obligatorio si rechazadas > 0
    defecto = None
    if valores["piezas_rechazadas"] > 0:
        if not defecto_id:
            raise CapturaInvalida("Selecciona un motivo de defecto cuando haya piezas rechazadas.")
        defecto = CatalogoDefecto.objects.filter(pk=defecto_id).first()
        if defecto is None:
            raise CapturaInvalida("El motivo de defecto seleccionado no es válido.")

    asignacion = (
        Asignacion.objects.filter(pk=asignacion_id, estacion__linea=linea, fecha=fecha)
        .select_related("estacion", "empleado")
        .first()
    )
    if asignacion is None:
        raise CapturaInvalida("La estación no pertenece a tu línea o a este turno.")
    if hora not in horas_del_turno(asignacion.turno):
        raise CapturaInvalida("La hora no pertenece a este turno.")

    # B-06: solo se captura el turno en curso. Sin esta regla, un POST con la
    # asignación del turno anterior corregía un turno ya cerrado. La restricción
    # aplica a la fecha de la guardia en curso; una fecha histórica sigue siendo
    # corregible.
    if fecha == fecha_guardia and asignacion.turno != turno_actual:
        raise CapturaInvalida("Ese turno ya está cerrado; solo se captura el turno en curso.")

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

        # Sincronizar el motivo de defecto asociado a la estación y al empleado
        registro.defectos.all().delete()
        if defecto is not None:
            DetalleDefecto.objects.create(
                registro=registro,
                defecto=defecto,
                cantidad=valores["piezas_rechazadas"],
            )

    return registro, creado