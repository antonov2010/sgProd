"""Pruebas del escenario de producción que usa la guía manual de US-15."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
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
