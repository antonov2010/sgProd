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


def crear_elegible(base_planta, indice, aceptadas=50):
    """Crea un operador con producción sin rechazos para probar la paginación."""
    operador = Empleado.objects.create(
        numero_empleado=f"OP-P{indice:02d}",
        nombre=f"Elegible {indice:02d}",
        rol=base_planta["op_limpio"].rol,
        linea=base_planta["est"].linea,
    )
    asignacion = Asignacion.objects.create(
        empleado=operador, estacion=base_planta["est"], turno=1
    )
    RegistroCalidadHorario.objects.create(
        asignacion=asignacion,
        hora=1,
        piezas_aceptadas=aceptadas,
        piezas_rechazadas=0,
    )
    return operador


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


def test_periodo_trae_etiqueta_legible_sin_cambiar_el_tipo(base_planta):
    """B-14: la pantalla usa una etiqueta corta; el enum interno sigue intacto."""
    periodo = calcular_elegibles_bono()["periodo"]
    assert periodo["etiqueta"] == "ventana móvil"
    assert periodo["tipo"] == "Últimos N días (ventana móvil)"

    hoy = date.today()
    ConfiguracionBono.objects.create(
        tipo_periodo="rango",
        fecha_inicio=hoy - timedelta(days=3),
        fecha_fin=hoy,
        activo=True,
    )
    periodo = calcular_elegibles_bono()["periodo"]
    assert periodo["etiqueta"] == "rango fijo"
    assert periodo["tipo"] == "Rango de fechas específico"


def test_la_lista_de_elegibles_se_pagina_de_diez_en_diez(client, entrar, base_planta):
    """RNF-4: 23 elegibles se reparten en 10 + 10 + 3 y la tarjeta conserva el total."""
    for indice in range(1, 24):
        crear_elegible(base_planta, indice)
    entrar("gerente")

    primera = client.get("/dashboard/gerente/")
    assert primera.status_code == 200
    html_primera = primera.content.decode()
    assert html_primera.count("data-elegible") == 10
    assert "Página 1 de 3" in html_primera
    assert "Total de elegibles: 23" in html_primera
    assert "Siguiente" in html_primera
    assert primera.context["pagina_elegibles"].paginator.count == 23

    ultima = client.get("/dashboard/gerente/?pagina=3")
    assert ultima.status_code == 200
    html_ultima = ultima.content.decode()
    assert html_ultima.count("data-elegible") == 3
    assert "Página 3 de 3" in html_ultima
    assert "Anterior" in html_ultima


def test_el_tablero_gerencial_muestra_la_etiqueta_del_periodo(client, entrar, base_planta):
    crear_elegible(base_planta, 1)
    entrar("gerente")

    html = client.get("/dashboard/gerente/").content.decode()

    assert "(ventana móvil)" in html
    assert "Últimos N días" not in html


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