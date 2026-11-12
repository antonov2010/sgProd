"""Pruebas de los umbrales configurables (US-13, criterio 4)."""

import pytest
from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError

from apps.dashboard.config_umbrales import umbrales_actuales
from apps.dashboard.datos_ejemplo import personal_ejemplo, registros_ejemplo
from apps.dashboard.models import UmbralSemaforo
from apps.dashboard.tablero import construir_tablero
from apps.dashboard.umbrales import UMBRALES

pytestmark = pytest.mark.django_db


def test_la_migracion_carga_los_valores_por_defecto():
    assert umbrales_actuales() == UMBRALES


def test_sin_filas_se_usan_los_valores_por_defecto():
    UmbralSemaforo.objects.all().delete()
    assert umbrales_actuales() == UMBRALES


def test_un_cambio_en_la_base_se_refleja_en_los_umbrales():
    UmbralSemaforo.objects.filter(indicador="fpy").update(verde=99.0, amarillo=97.0)
    actuales = umbrales_actuales()
    assert actuales["fpy"] == {"verde": 99.0, "amarillo": 97.0, "mejor": "alto"}
    assert actuales["defectos"] == UMBRALES["defectos"]


def test_el_tablero_cambia_de_color_sin_tocar_codigo():
    registros, personal = registros_ejemplo(), personal_ejemplo()
    antes = construir_tablero(registros, personal, umbrales_actuales())
    UmbralSemaforo.objects.filter(indicador="fpy").update(verde=99.9, amarillo=99.5)
    despues = construir_tablero(registros, personal, umbrales_actuales())
    estados_antes = [linea["estado"] for linea in antes["lineas"]]
    estados_despues = [linea["estado"] for linea in despues["lineas"]]
    assert estados_antes != estados_despues
    assert "bad" in estados_despues


def test_la_pantalla_usa_los_umbrales_de_la_base(client):
    UmbralSemaforo.objects.filter(indicador="fpy").update(verde=99.9, amarillo=99.5)
    respuesta = client.get("/dashboard/gerente/")
    assert respuesta.status_code == 200
    assert respuesta.context["tablero"]["lineas"][0]["fpy"] is not None
    assert "99.9" in respuesta.content.decode() or "99,9" in respuesta.content.decode()


def test_valida_que_el_verde_no_quede_peor_que_el_amarillo():
    with pytest.raises(ValidationError):
        UmbralSemaforo(indicador="fpy", verde=80, amarillo=90).full_clean(validate_unique=False)
    with pytest.raises(ValidationError):
        UmbralSemaforo(indicador="defectos", verde=8, amarillo=3).full_clean(validate_unique=False)
    with pytest.raises(ValidationError):
        UmbralSemaforo(indicador="fpy", verde=120, amarillo=90).full_clean(validate_unique=False)


def test_los_umbrales_se_editan_desde_el_admin():
    assert UmbralSemaforo in site._registry
