"""Pruebas del acomodo del tablero gerencial (lote D)."""

import re

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.calidad.models import Asignacion, RegistroCalidadHorario
from apps.personal.models import Empleado, Estacion, Linea, Rol

pytestmark = pytest.mark.django_db


@pytest.fixture
def captura_gerente(entrar):
    """Una línea con captura real para que el tablero no caiga en ejemplo."""
    entrar("gerente")
    rol_operador, _ = Rol.objects.get_or_create(
        tipo_rol="operador", defaults={"nombre": "Operador"}
    )
    linea = Linea.objects.create(nombre="Línea 3")
    operador = Empleado.objects.create(
        numero_empleado="OP-G1",
        nombre="Luis Operador",
        rol=rol_operador,
        linea=linea,
    )
    estacion = Estacion.objects.create(linea=linea, nombre="Soldadura", orden=1)
    asignacion = Asignacion.objects.create(
        empleado=operador,
        estacion=estacion,
        fecha=timezone.localdate(),
        turno=1,
    )
    RegistroCalidadHorario.objects.create(
        asignacion=asignacion,
        hora=8,
        piezas_aceptadas=39,
        piezas_rechazadas=1,
        piezas_retrabajo=0,
    )
    return linea


def test_por_turno_es_un_details_cerrado_con_chips(client, captura_gerente):
    html = client.get(reverse("dashboard:pantalla_gerente")).content.decode()

    detalle = re.search(r"<details[^>]*class=\"tg-plegable\"[^>]*>.*?</details>", html, re.S)
    assert detalle is not None
    bloque = detalle.group(0)
    assert "<summary" in bloque
    assert "Por turno" in bloque
    assert "1 turno" in bloque
    assert "Turno 1" in bloque
    assert "tg-chip" in bloque
    assert ">FPY<" in bloque
    assert ">Defectos<" in bloque
    assert " open" not in detalle.group(0).split(">", 1)[0]


def test_la_tendencia_va_tras_las_lineas_y_antes_de_piezas(client, captura_gerente):
    html = client.get(reverse("dashboard:pantalla_gerente")).content.decode()

    assert html.index("Líneas de producción") < html.index("Tendencia hora por hora")
    assert html.index("Tendencia hora por hora") < html.index("Piezas por hora vs meta")
    # El panel conserva el id que usa «Ver tendencia» y su estado accesible.
    assert 'id="g-l1"' in html
    assert 'aria-controls="g-l1"' in html
    assert 'aria-expanded="true"' in html
