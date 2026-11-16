"""Pruebas de los indicadores del turno en el tablero del jefe (lote D)."""

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.calidad import services
from apps.calidad.models import Asignacion, RegistroCalidadHorario
from apps.personal.models import Empleado, Estacion, Linea, Rol

pytestmark = pytest.mark.django_db


@pytest.fixture
def reloj_de_manana(monkeypatch):
    """Fija el reloj a las 09:00: turno 1 y fecha de guardia de hoy."""
    monkeypatch.setattr(services, "hora_actual", lambda: 9)


@pytest.fixture
def linea_con_captura(entrar, reloj_de_manana):
    """Línea con 4 estaciones, 3 asignadas y captura en dos horas del turno.

    La estación 4 queda sin operador para probar la cobertura «3 de 4».
    """
    jefe = entrar("jefe", numero="J-01")
    rol_operador, _ = Rol.objects.get_or_create(
        tipo_rol="operador", defaults={"nombre": "Operador"}
    )
    linea = Linea.objects.create(nombre="Línea del jefe", jefe_linea=jefe)
    jefe.linea = linea
    jefe.save(update_fields=["linea"])

    estaciones = [
        Estacion.objects.create(linea=linea, nombre=f"Estación {i}", orden=i)
        for i in range(1, 5)
    ]
    operadores = [
        Empleado.objects.create(
            numero_empleado=f"OP-{i}",
            nombre=f"Operador {i}",
            rol=rol_operador,
            linea=linea,
        )
        for i in range(1, 4)
    ]
    fecha = timezone.localdate()
    asignaciones = [
        Asignacion.objects.create(
            empleado=operador, estacion=estacion, fecha=fecha, turno=1
        )
        for operador, estacion in zip(operadores, estaciones)
    ]

    # 17 aceptadas de 20 piezas del turno => FPY 85.0 %.
    RegistroCalidadHorario.objects.create(
        asignacion=asignaciones[0],
        hora=8,
        piezas_aceptadas=9,
        piezas_rechazadas=1,
        piezas_retrabajo=0,
    )
    RegistroCalidadHorario.objects.create(
        asignacion=asignaciones[1],
        hora=9,
        piezas_aceptadas=8,
        piezas_rechazadas=1,
        piezas_retrabajo=1,
    )
    return linea


def _kpis(respuesta):
    return {k["clave"]: k for k in respuesta.context["indicadores"]}


def test_los_tres_kpis_del_turno_usan_los_datos_capturados(client, linea_con_captura):
    respuesta = client.get(reverse("dashboard:pantalla_jefe"))

    assert respuesta.status_code == 200
    kpis = _kpis(respuesta)
    assert kpis["fpy"]["valor"] == "85.0"
    assert kpis["fpy"]["unidad"] == "%"
    assert kpis["cobertura"]["valor"] == "3"
    assert kpis["cobertura"]["unidad"] == "de 4"
    assert kpis["capturas"]["valor"] == "1"
    assert kpis["capturas"]["unidad"] == "de 4"

    html = respuesta.content.decode()
    assert 'aria-label="Indicadores del turno en curso"' in html
    assert "FPY del turno" in html
    assert "Cobertura de estaciones" in html
    assert "Capturas de la hora" in html


def test_sin_captura_el_fpy_muestra_guion_y_las_capturas_cero(client, linea_con_captura):
    RegistroCalidadHorario.objects.all().delete()

    respuesta = client.get(reverse("dashboard:pantalla_jefe"))

    assert respuesta.status_code == 200
    kpis = _kpis(respuesta)
    assert kpis["fpy"]["valor"] == "—"
    assert "Sin datos" in kpis["fpy"]["contexto"]
    assert kpis["cobertura"]["valor"] == "3"
    assert kpis["cobertura"]["unidad"] == "de 4"
    assert kpis["capturas"]["valor"] == "0"
    assert kpis["capturas"]["unidad"] == "de 4"


def test_un_jefe_sin_linea_no_rompe_el_tablero(client, entrar, reloj_de_manana):
    entrar("jefe", numero="J-02")

    respuesta = client.get(reverse("dashboard:pantalla_jefe"))

    assert respuesta.status_code == 200
    kpis = _kpis(respuesta)
    assert kpis["fpy"]["valor"] == "—"
    assert kpis["cobertura"]["valor"] == "0"
    assert kpis["cobertura"]["unidad"] == "de 0"
    assert kpis["capturas"]["valor"] == "0"
    assert kpis["capturas"]["unidad"] == "de 0"
