"""Pruebas de acceso a los tableros: solo entra el rol que corresponde."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

PANTALLAS = {
    "gerente": "dashboard:pantalla_gerente",
    "jefe": "dashboard:pantalla_jefe",
    "operador": "dashboard:pantalla_operador",
}


@pytest.mark.parametrize("rol", PANTALLAS)
def test_sin_sesion_redirige_al_login(client, rol):
    respuesta = client.get(reverse(PANTALLAS[rol]))
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("personal:login")


@pytest.mark.parametrize("rol", PANTALLAS)
def test_cada_rol_entra_a_su_pantalla(client, entrar, rol):
    entrar(rol)
    assert client.get(reverse(PANTALLAS[rol])).status_code == 200


@pytest.mark.parametrize(
    "rol,ajena",
    [
        ("gerente", "jefe"),
        ("gerente", "operador"),
        ("jefe", "gerente"),
        ("jefe", "operador"),
        ("operador", "gerente"),
        ("operador", "jefe"),
    ],
)
def test_un_rol_no_entra_a_la_pantalla_de_otro(client, entrar, rol, ajena):
    entrar(rol)
    assert client.get(reverse(PANTALLAS[ajena])).status_code == 403


def test_el_403_usa_la_pagina_propia_con_lenguaje_del_sitio(client, entrar):
    """B-14: el rol equivocado ve una página 403 navegable, no la cruda de Django."""
    entrar("operador")
    respuesta = client.get(reverse(PANTALLAS["gerente"]))

    assert respuesta.status_code == 403
    html = respuesta.content.decode()
    assert "No tienes acceso a esta pantalla" in html
    assert "Volver al inicio" in html
    assert "Cerrar sesión" in html


def test_el_operador_no_ve_los_datos_del_gerente(client, entrar):
    entrar("operador")
    respuesta = client.get(reverse(PANTALLAS["gerente"]))
    assert respuesta.status_code == 403
    assert "FPY de planta" not in respuesta.content.decode()


def test_un_empleado_inactivo_pierde_el_acceso(client, entrar):
    empleado = entrar("gerente")
    empleado.activo = False
    empleado.save()
    respuesta = client.get(reverse(PANTALLAS["gerente"]))
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("personal:login")


def test_una_sesion_con_empleado_inexistente_redirige(client, db):
    sesion = client.session
    sesion["empleado_id"] = 999999
    sesion.save()
    respuesta = client.get(reverse(PANTALLAS["gerente"]))
    assert respuesta.status_code == 302


def test_el_login_de_gerente_lleva_a_su_tablero(client, entrar):
    gerente = entrar("gerente")
    gerente.set_pin("123456")
    gerente.save(update_fields=["pin_hash"])
    sesion = client.session
    sesion.flush()
    respuesta = client.post(
        reverse("personal:login"),
        {"numero_empleado": gerente.numero_empleado, "pin": "123456"},
        follow=True,
    )
    assert respuesta.status_code == 200
    assert respuesta.redirect_chain[-1][0] == reverse(PANTALLAS["gerente"])
