"""Pruebas de la configuración editable desde el Admin (US-14, RF-3.2)."""

import pytest
from django.contrib.admin.sites import site
from django.urls import reverse

from apps.personal.models import Estacion, Linea

from .models import MetaEstacion

pytestmark = pytest.mark.django_db


def test_la_meta_por_estacion_se_edita_desde_el_admin():
    assert MetaEstacion in site._registry


def test_el_admin_guarda_el_cambio_de_la_meta(admin_client):
    linea = Linea.objects.create(nombre="Línea 9")
    estacion = Estacion.objects.create(linea=linea, nombre="Estación 9", orden=1)
    meta = MetaEstacion.objects.create(estacion=estacion, piezas_por_hora_meta=100)

    respuesta = admin_client.post(
        reverse("admin:dashboard_metaestacion_change", args=[meta.pk]),
        {"estacion": estacion.pk, "piezas_por_hora_meta": 140},
    )

    assert respuesta.status_code == 302
    meta.refresh_from_db()
    assert meta.piezas_por_hora_meta == 140
