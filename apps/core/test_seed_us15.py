"""Pruebas del escenario de producción que usa la guía manual de US-15."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum
from django.utils import timezone

from apps.calidad.models import Asignacion, DetalleDefecto, RegistroCalidadHorario
from apps.dashboard.bonos import calcular_elegibles_bono
from apps.dashboard.models import ConfiguracionBono
from apps.personal.models import Empleado, Linea, NivelHabilidad, SkillMatrix

pytestmark = pytest.mark.django_db


def _cargar_escenario_us15(empleados=30):
    salida = StringIO()
    call_command(
        "seed_demo",
        reset=True,
        empleados=empleados,
        us15=True,
        stdout=salida,
    )
    return salida.getvalue()


def test_seed_us15_crea_los_casos_de_bono_y_respeta_el_periodo():
    salida = _cargar_escenario_us15()
    hoy = timezone.localdate()

    assert "Casos de prueba US-15" in salida
    assert "docs/04_guia_pruebas_us15.md" in salida
    assert ConfiguracionBono.objects.filter(activo=True, dias_evaluacion=14).count() == 1
    assert Asignacion.objects.count() == 5 * 8 * 14
    assert RegistroCalidadHorario.objects.count() == 5 * 8 * 14 * 8

    assert not Linea.objects.filter(jefe_linea__isnull=True).exists()
    assert not Empleado.objects.filter(
        rol__tipo_rol="operador", linea__isnull=True
    ).exists()

    detalle_antiguo = (
        DetalleDefecto.objects.select_related("registro__asignacion__empleado")
        .filter(registro__asignacion__fecha=hoy - timedelta(days=10))
        .first()
    )
    detalle_reciente = (
        DetalleDefecto.objects.select_related("registro__asignacion__empleado")
        .filter(registro__asignacion__fecha=hoy - timedelta(days=1))
        .first()
    )
    assert detalle_antiguo is not None
    assert detalle_reciente is not None
    antiguo = detalle_antiguo.registro.asignacion.empleado
    reciente = detalle_reciente.registro.asignacion.empleado

    elegibles_14 = {
        item["numero_empleado"] for item in calcular_elegibles_bono()["elegibles"]
    }
    assert antiguo.numero_empleado not in elegibles_14
    assert reciente.numero_empleado not in elegibles_14

    configuracion = ConfiguracionBono.objects.get(activo=True)
    configuracion.dias_evaluacion = 7
    configuracion.save(update_fields=["dias_evaluacion"])

    elegibles_7 = {
        item["numero_empleado"] for item in calcular_elegibles_bono()["elegibles"]
    }
    assert antiguo.numero_empleado in elegibles_7
    assert reciente.numero_empleado not in elegibles_7


def test_seed_us15_deja_un_principiante_por_linea():
    _cargar_escenario_us15()

    lineas = list(Linea.objects.order_by("nombre"))
    assert lineas

    sin_principiante = []
    for linea in lineas:
        operadores = Empleado.objects.filter(
            linea=linea, activo=True, rol__tipo_rol="operador"
        )
        tiene_principiante = SkillMatrix.objects.filter(
            empleado__in=operadores,
            estacion__linea=linea,
            nivel=NivelHabilidad.PRINCIPIANTE,
        ).exists()
        if not tiene_principiante:
            sin_principiante.append(linea.nombre)

    assert not sin_principiante, (
        "Líneas sin un operador Principiante (por Empleado.linea) en una "
        f"estación de su línea: {sin_principiante}"
    )


def test_seed_sin_us15_tambien_ubica_al_personal_y_deja_un_principiante():
    """``_asignar_lineas`` no depende de --us15 y la garantía también aplica."""
    salida = StringIO()
    call_command("seed_demo", reset=True, empleados=30, stdout=salida)

    assert not Asignacion.objects.exists()
    assert not Empleado.objects.filter(
        rol__tipo_rol="operador", linea__isnull=True
    ).exists()
    for linea in Linea.objects.all():
        assert SkillMatrix.objects.filter(
            empleado__linea=linea,
            estacion__linea=linea,
            nivel=NivelHabilidad.PRINCIPIANTE,
        ).exists(), f"{linea.nombre} sin Principiante visible por Empleado.linea"


def test_seed_us15_exige_reset_para_ser_reproducible():
    with pytest.raises(CommandError, match="--reset"):
        call_command("seed_demo", empleados=10, us15=True, stdout=StringIO())


def _fpy_ultimo_dia(nombre_linea):
    """FPY del día más reciente con las sumas reales de RegistroCalidadHorario."""
    totales = RegistroCalidadHorario.objects.filter(
        asignacion__estacion__linea__nombre=nombre_linea,
        asignacion__fecha=timezone.localdate(),
    ).aggregate(
        aceptadas=Sum("piezas_aceptadas"),
        rechazadas=Sum("piezas_rechazadas"),
        retrabajo=Sum("piezas_retrabajo"),
    )
    total = totales["aceptadas"] + totales["rechazadas"] + totales["retrabajo"]
    return round(100 * totales["aceptadas"] / total, 1)


def test_seed_us15_variar_calidad_de_linea_4_y_linea_6():
    salida = _cargar_escenario_us15()

    assert _fpy_ultimo_dia("Línea 4") == 75.0
    assert _fpy_ultimo_dia("Línea 6") == 83.0
    assert "Línea 4 75.0 %" in salida
    assert "Línea 6 83.0 %" in salida


def test_seed_us15_la_variacion_respeta_los_casos_de_bono():
    _cargar_escenario_us15()
    hoy = timezone.localdate()

    assert Asignacion.objects.count() == 560
    assert RegistroCalidadHorario.objects.count() == 4480

    elegibles = {
        item["numero_empleado"] for item in calcular_elegibles_bono()["elegibles"]
    }
    for nombre in ("Línea 4", "Línea 6"):
        operadores = list(
            Empleado.objects.filter(
                linea__nombre=nombre, rol__tipo_rol="operador", activo=True
            ).order_by("numero_empleado")
        )
        limpio, antiguo, reciente = operadores[:3]

        assert not RegistroCalidadHorario.objects.filter(
            asignacion__empleado=limpio, piezas_rechazadas__gt=0
        ).exists()
        assert limpio.numero_empleado in elegibles

        # El caso antiguo conserva solo sus defectos de hace 10 días (todas sus
        # asignaciones de ese día en la hora 9), sin rechazadas de hoy.
        detalles_antiguo = list(
            DetalleDefecto.objects.filter(
                registro__asignacion__empleado=antiguo
            )
        )
        assert len(detalles_antiguo) == Asignacion.objects.filter(
            empleado=antiguo, fecha=hoy - timedelta(days=10)
        ).count()
        assert {d.registro.asignacion.fecha for d in detalles_antiguo} == {
            hoy - timedelta(days=10)
        }
        assert {d.registro.hora for d in detalles_antiguo} == {9}
        assert {d.cantidad for d in detalles_antiguo} == {2}

        # El caso reciente conserva solo su defecto de ayer (hora 10).
        detalles_reciente = list(
            DetalleDefecto.objects.filter(
                registro__asignacion__empleado=reciente
            )
        )
        assert len(detalles_reciente) == Asignacion.objects.filter(
            empleado=reciente, fecha=hoy - timedelta(days=1)
        ).count()
        assert {d.registro.asignacion.fecha for d in detalles_reciente} == {
            hoy - timedelta(days=1)
        }
        assert {d.registro.hora for d in detalles_reciente} == {10}
        assert {d.cantidad for d in detalles_reciente} == {1}

        assert antiguo.numero_empleado not in elegibles
        assert reciente.numero_empleado not in elegibles

    # Cada rechazada repartida hoy tiene su DetalleDefecto con la misma cantidad.
    for registro in RegistroCalidadHorario.objects.filter(
        asignacion__estacion__linea__nombre__in=("Línea 4", "Línea 6"),
        asignacion__fecha=hoy,
        piezas_rechazadas__gt=0,
    ):
        assert registro.piezas_rechazadas <= 9999
        assert (
            sum(registro.defectos.values_list("cantidad", flat=True))
            == registro.piezas_rechazadas
        )
