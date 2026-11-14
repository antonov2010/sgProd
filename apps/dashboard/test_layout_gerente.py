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


def _registrar_operador(linea, estacion, rol, numero, nombre, aceptadas=40):
    """Crea un operador con producción limpia para el tablero y los bonos."""
    operador = Empleado.objects.create(
        numero_empleado=numero,
        nombre=nombre,
        rol=rol,
        linea=linea,
    )
    asignacion = Asignacion.objects.create(
        empleado=operador,
        estacion=estacion,
        turno=1,
    )
    RegistroCalidadHorario.objects.create(
        asignacion=asignacion,
        hora=1,
        piezas_aceptadas=aceptadas,
        piezas_rechazadas=0,
    )
    return operador


@pytest.fixture
def cinco_lineas(entrar):
    """Cinco líneas con captura real: las cinco tarjetas del carrusel."""
    entrar("gerente")
    rol, _ = Rol.objects.get_or_create(
        tipo_rol="operador", defaults={"nombre": "Operador"}
    )
    for numero in range(1, 6):
        linea = Linea.objects.create(nombre=f"Línea {numero}")
        estacion = Estacion.objects.create(linea=linea, nombre="Ensamble", orden=1)
        _registrar_operador(
            linea, estacion, rol, f"OP-L{numero}", f"Operador L{numero}"
        )


@pytest.fixture
def doce_elegibles(entrar):
    """Doce elegibles: la tabla se reparte en 10 + 2 y la URL lleva el hash."""
    entrar("gerente")
    rol, _ = Rol.objects.get_or_create(
        tipo_rol="operador", defaults={"nombre": "Operador"}
    )
    linea = Linea.objects.create(nombre="Línea bonos")
    estacion = Estacion.objects.create(linea=linea, nombre="Ensamble", orden=1)
    for numero in range(1, 13):
        _registrar_operador(
            linea,
            estacion,
            rol,
            f"OP-B{numero:02d}",
            f"Elegible {numero:02d}",
        )


def test_el_html_no_expone_comentarios_de_plantilla(client, captura_gerente):
    html = client.get(reverse("dashboard:pantalla_gerente")).content.decode()

    assert "{#" not in html
    assert "Bloque paginado de elegibles" not in html

    fragmento = client.get(
        "/dashboard/gerente/?pagina=1&fragmento=bonos"
    ).content.decode()
    assert "{#" not in fragmento
    assert "Bloque paginado de elegibles" not in fragmento


def test_secciones_en_orden_y_con_separadores(client, captura_gerente):
    html = client.get(reverse("dashboard:pantalla_gerente")).content.decode()

    secciones = [
        "indicadores-planta",
        "lineas-produccion",
        "tendencia-hora",
        "produccion-defectos",
        "reconocimiento",
    ]
    posiciones = [html.index(f'id="{seccion}"') for seccion in secciones]
    assert posiciones == sorted(posiciones)
    # Indicadores → Líneas → Tendencia → Producción → Reconocimiento.
    assert len(posiciones) == 5
    assert html.count('<hr class="sg-dash-sep">') >= 4

    for seccion in secciones:
        assert re.search(
            rf'<section[^>]*id="{seccion}"[^>]*aria-labelledby="titulo-', html
        )
    assert html.count("<h2") >= 5


def test_el_carrusel_expone_controles_y_las_cinco_tarjetas(client, cinco_lineas):
    html = client.get(reverse("dashboard:pantalla_gerente")).content.decode()

    assert 'role="region"' in html
    assert 'aria-roledescription="carrusel"' in html
    assert 'aria-label="Línea anterior"' in html
    assert 'aria-label="Línea siguiente"' in html
    assert html.count('data-linea="') == 5

    pista = re.search(
        r'data-carrusel-pista>(.*?)</div>\s*<div class="tg-carrusel__controles"',
        html,
        re.S,
    )
    assert pista is not None
    assert pista.group(1).count('data-linea="') == 5
    # Sin JavaScript las tarjetas quedan visibles (nada de hidden ni vacío).
    for tarjeta in re.findall(r'<article[^>]*data-linea="[^"]+"[^>]*>', html):
        assert "hidden" not in tarjeta


def test_el_carrusel_base_no_tiene_clones_ni_ids_duplicados(client, cinco_lineas):
    """Los clones del bucle infinito los agrega el JS; el HTML base no los trae."""
    html = client.get(reverse("dashboard:pantalla_gerente")).content.decode()

    assert not re.search(r"<article[^>]*data-clon", html)
    assert html.count('data-linea="') == 5

    ids = re.findall(r'\bid="([^"]+)"', html)
    assert ids
    assert len(ids) == len(set(ids))


def test_paginacion_conserva_el_hash_y_el_bloque_de_la_tabla(client, doce_elegibles):
    html = client.get(reverse("dashboard:pantalla_gerente")).content.decode()

    assert 'id="bonos-tabla"' in html
    assert 'tabindex="-1"' in html
    assert 'aria-live="polite"' in html
    assert 'href="?pagina=2#reconocimiento"' in html
    assert html.count("data-elegible") == 10
    assert "Total de elegibles: 12" in html
    assert "Página 1 de 2" in html
    assert "Mostrando 1–10 de 12" in html

    # El fetch pide solo el bloque, que conserva su id y su paginación.
    fragmento = client.get(
        "/dashboard/gerente/?pagina=2&fragmento=bonos"
    ).content.decode()
    assert "<html" not in fragmento.lower()
    assert 'id="bonos-tabla"' in fragmento
    assert fragmento.count("data-elegible") == 2
    assert 'href="?pagina=1#reconocimiento"' in fragmento
    assert "Página 2 de 2" in fragmento
    assert "Mostrando 11–12 de 12" in fragmento
