"""Pruebas de elegibles a bono por cero defectos (US-15)."""

from datetime import date, timedelta

import pytest

from apps.calidad.models import Asignacion, RegistroCalidadHorario
from apps.dashboard.bonos import calcular_elegibles_bono
from apps.dashboard.models import ConfiguracionBono
from apps.personal.models import Empleado, Estacion, Linea, Rol

pytestmark = pytest.mark.django_db


@pytest.fixture
def base_planta():
    rol_op = Rol.objects.create(nombre="Operador", tipo_rol="operador")
    linea = Linea.objects.create(nombre="Línea 1")
    est = Estacion.objects.create(linea=linea, nombre="Ensamble", orden=1)
    op_limpio = Empleado.objects.create(
        numero_empleado="OP-01", nombre="Carlos Cero", rol=rol_op, linea=linea
    )
    op_defecto = Empleado.objects.create(
        numero_empleado="OP-02", nombre="Mario Rechazo", rol=rol_op, linea=linea
    )
    return {"est": est, "op_limpio": op_limpio, "op_defecto": op_defecto}


def test_operador_sin_defectos_aparece_y_con_defecto_se_excluye(base_planta):
    a1 = Asignacion.objects.create(
        empleado=base_planta["op_limpio"], estacion=base_planta["est"], turno=1
    )
    RegistroCalidadHorario.objects.create(
        asignacion=a1, hora=1, piezas_aceptadas=50, piezas_rechazadas=0
    )
    RegistroCalidadHorario.objects.create(
        asignacion=a1, hora=2, piezas_aceptadas=45, piezas_rechazadas=0
    )

    a2 = Asignacion.objects.create(
        empleado=base_planta["op_defecto"], estacion=base_planta["est"], turno=1
    )
    RegistroCalidadHorario.objects.create(
        asignacion=a2, hora=1, piezas_aceptadas=50, piezas_rechazadas=0
    )
    RegistroCalidadHorario.objects.create(
        asignacion=a2, hora=2, piezas_aceptadas=40, piezas_rechazadas=1
    )

    res = calcular_elegibles_bono()
    nombres = [e["nombre"] for e in res["elegibles"]]
    assert nombres == ["Carlos Cero"]
    assert res["elegibles"][0]["aceptadas"] == 95
    assert res["elegibles"][0]["rechazadas"] == 0
    assert len(res["elegibles"][0]["registros"]) == 2


def test_periodo_configurable_recalcula_sin_tocar_codigo(base_planta):
    hoy = date.today()
    hace_10_dias = hoy - timedelta(days=10)

    a_vieja = Asignacion.objects.create(
        empleado=base_planta["op_limpio"], estacion=base_planta["est"], turno=1
    )
    Asignacion.objects.filter(pk=a_vieja.pk).update(fecha=hace_10_dias)
    RegistroCalidadHorario.objects.create(
        asignacion=a_vieja, hora=1, piezas_aceptadas=30, piezas_rechazadas=2
    )

    a_hoy = Asignacion.objects.create(
        empleado=base_planta["op_limpio"], estacion=base_planta["est"], turno=1
    )
    RegistroCalidadHorario.objects.create(
        asignacion=a_hoy, hora=1, piezas_aceptadas=40, piezas_rechazadas=0
    )

    ConfiguracionBono.objects.create(tipo_periodo="dias", dias_evaluacion=7, activo=True)
    assert [e["nombre"] for e in calcular_elegibles_bono()["elegibles"]] == ["Carlos Cero"]

    ConfiguracionBono.objects.update(dias_evaluacion=15)
    assert calcular_elegibles_bono()["elegibles"] == []


def test_gerente_consulta_lista_y_detalle_de_elegible(client, entrar, base_planta):
    a1 = Asignacion.objects.create(
        empleado=base_planta["op_limpio"], estacion=base_planta["est"], turno=1
    )
    RegistroCalidadHorario.objects.create(
        asignacion=a1, hora=1, piezas_aceptadas=60, piezas_rechazadas=0
    )

    entrar("gerente")
    resp_lista = client.get("/dashboard/gerente/")
    assert resp_lista.status_code == 200
    assert "Carlos Cero" in resp_lista.content.decode()

    resp_detalle = client.get(f"/dashboard/gerente/bono/{base_planta['op_limpio'].id}/")
    assert resp_detalle.status_code == 200
    html = resp_detalle.content.decode()
    assert "Carlos Cero" in html
    assert "Ensamble" in html
    assert "60" in html