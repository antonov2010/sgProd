"""Pruebas de la conexión del tablero con la base de datos (US-13)."""

import pytest

from apps.calidad.models import Asignacion, RegistroCalidadHorario
from apps.dashboard.datos_reales import personal_real, registros_reales
from apps.dashboard.models import MetaEstacion
from apps.dashboard.tablero import construir_tablero
from apps.personal.models import Empleado, Estacion, Linea, Rol

pytestmark = pytest.mark.django_db


@pytest.fixture
def escenario():
    rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")
    rol_op = Rol.objects.create(nombre="Operador", tipo_rol="operador")
    linea = Linea.objects.create(nombre="Línea 3")
    jefe = Empleado.objects.create(numero_empleado="J1", nombre="Ana Jefa", rol=rol_jefe, linea=linea)
    linea.jefe_linea = jefe
    linea.save()
    op = Empleado.objects.create(numero_empleado="O1", nombre="Luis Operador", rol=rol_op, linea=linea)
    Empleado.objects.create(numero_empleado="O2", nombre="Baja Inactivo", rol=rol_op, linea=linea, activo=False)
    est = Estacion.objects.create(linea=linea, nombre="Soldadura", orden=1)
    MetaEstacion.objects.create(estacion=est, piezas_por_hora_meta=40)
    asig = Asignacion.objects.create(empleado=op, estacion=est, turno=1)
    for hora, (a, r, t) in {2: (38, 1, 1), 1: (40, 0, 0)}.items():
        RegistroCalidadHorario.objects.create(
            asignacion=asig, hora=hora, piezas_aceptadas=a, piezas_rechazadas=r, piezas_retrabajo=t
        )
    return linea


def test_sin_captura_devuelve_lista_vacia():
    assert registros_reales() == []


def test_registros_reales_tienen_la_forma_esperada_y_van_ordenados(escenario):
    regs = registros_reales()
    assert [r["hora"] for r in regs] == ["Hora 1", "Hora 2"]
    assert regs[0] == {
        "linea": "Línea 3", "estacion": "Soldadura", "empleado": "Luis Operador",
        "hora": "Hora 1", "aceptadas": 40, "rechazadas": 0, "retrabajo": 0, "meta": 40,
    }


def test_estacion_sin_meta_usa_el_valor_por_defecto(escenario):
    MetaEstacion.objects.all().delete()
    assert {r["meta"] for r in registros_reales()} == {100}


def test_personal_real_solo_operadores_activos_y_jefe(escenario):
    assert personal_real() == {"Línea 3": {"jefe": "Ana Jefa", "operadores": ["Luis Operador"]}}


def test_el_tablero_se_arma_con_datos_reales(escenario):
    t = construir_tablero(registros_reales(), personal_real())
    assert len(t["lineas"]) == 1
    assert t["lineas"][0]["nombre"] == "Línea 3"
    assert t["lineas"][0]["personal"]["jefe"] == "Ana Jefa"
    assert t["empleados"][0]["nombre"] == "Luis Operador"


def test_la_pantalla_usa_ejemplo_si_no_hay_captura(client):
    r = client.get("/dashboard/gerente/")
    assert r.status_code == 200
    assert r.context["tablero_es_ejemplo"] is True
    assert "Datos de ejemplo" in r.content.decode()


def test_la_pantalla_usa_datos_reales_si_hay_captura(client, escenario):
    r = client.get("/dashboard/gerente/")
    assert r.context["tablero_es_ejemplo"] is False
    assert "Datos reales" in r.content.decode()
