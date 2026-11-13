"""Pruebas de la API REST y de su documentación Swagger.

Cubren lo que puede romperse sin que se note: que el esquema OpenAPI se
genere, que la UI de Swagger cargue, que la API exija autenticación y que el
POST de la matriz se comporte igual por la ruta REST y por la ruta HTML.
"""

import base64

import pytest
import yaml
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.personal.models import Empleado, Estacion, Linea, NivelHabilidad, Rol, SkillMatrix

User = get_user_model()


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        username="revisor", password="ClaveSegura123", is_staff=True
    )


@pytest.fixture
def planta(db):
    rol = Rol.objects.create(nombre="Operador", tipo_rol="operador")
    rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")
    linea = Linea.objects.create(nombre="Línea 3")
    estacion = Estacion.objects.create(linea=linea, nombre="Corte", orden=1)
    empleado = Empleado.objects.create(
        numero_empleado="SG-0100",
        nombre="Ana Activa",
        pin="1234",
        rol=rol,
        linea=linea,
    )
    jefe = Empleado.objects.create(
        numero_empleado="SG-0002",
        nombre="Rocío Salas",
        pin="1234",
        rol=rol_jefe,
        linea=linea,
    )
    return {
        "linea": linea,
        "estacion": estacion,
        "empleado": empleado,
        "jefe": jefe,
    }


# --- Documentación -------------------------------------------------------


def test_esquema_openapi_se_genera(client):
    respuesta = client.get(reverse("api:schema"))

    assert respuesta.status_code == 200
    esquema = yaml.safe_load(respuesta.content)
    assert esquema["openapi"].startswith("3.")
    assert esquema["info"]["title"] == "SG-Prod API"
    assert "/api/empleados/" in esquema["paths"]
    assert "/api/matriz/nivel/" in esquema["paths"]


def test_swagger_ui_carga(client):
    respuesta = client.get(reverse("api:swagger-ui"))

    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert "swagger-ui" in contenido
    assert reverse("api:schema") in contenido


def test_apicenter_redirige_a_la_documentacion(client):
    respuesta = client.get("/api/")

    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("api:swagger-ui")


def test_redoc_carga(client):
    respuesta = client.get(reverse("api:redoc"))

    assert respuesta.status_code == 200


# --- Autenticación -------------------------------------------------------


def test_anonimo_no_puede_leer_empleados(client):
    respuesta = client.get(reverse("api:empleado-list"))

    assert respuesta.status_code in (401, 403)


def test_empleado_autenticado_no_expone_el_pin(client, usuario, planta):
    client.force_login(usuario)

    respuesta = client.get(reverse("api:empleado-list"))

    assert respuesta.status_code == 200
    assert "pin" not in respuesta.json()["results"][0]


def test_listado_paginado_y_busqueda(client, usuario, planta):
    client.force_login(usuario)

    respuesta = client.get(reverse("api:empleado-list"), {"search": "Ana"})

    assert respuesta.status_code == 200
    assert respuesta.json()["count"] == 1


def test_detalle_de_empleado(client, usuario, planta):
    client.force_login(usuario)
    empleado = planta["empleado"]

    respuesta = client.get(reverse("api:empleado-detail", args=[empleado.pk]))

    assert respuesta.status_code == 200
    assert respuesta.json()["numero_empleado"] == "SG-0100"


# --- POST de la matriz ---------------------------------------------------


def test_post_crea_el_nivel(client, usuario, planta):
    client.force_login(usuario)

    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": NivelHabilidad.EXPERTO,
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"success": True, "nivel": "Experto"}
    assert SkillMatrix.objects.get().nivel == "Experto"


def test_post_actualiza_el_nivel_existente(client, usuario, planta):
    client.force_login(usuario)
    SkillMatrix.objects.create(
        empleado=planta["empleado"],
        estacion=planta["estacion"],
        nivel=NivelHabilidad.PRINCIPIANTE,
    )

    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": NivelHabilidad.INSTRUCTOR,
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    assert SkillMatrix.objects.get().nivel == "Instructor"


def test_post_sin_nivel_borra_la_fila(client, usuario, planta):
    client.force_login(usuario)
    SkillMatrix.objects.create(
        empleado=planta["empleado"],
        estacion=planta["estacion"],
        nivel=NivelHabilidad.EXPERTO,
    )

    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": "Sin nivel",
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    assert not SkillMatrix.objects.exists()


def test_post_con_nivel_invalido_responde_400(client, usuario, planta):
    client.force_login(usuario)

    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": "Dios",
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["success"] is False


def test_post_con_empleado_inexistente_responde_404(client, usuario, planta):
    client.force_login(usuario)

    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": 999999,
            "estacion_id": planta["estacion"].pk,
            "nivel": NivelHabilidad.EXPERTO,
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "Empleado no encontrado"


def test_anonimo_no_puede_escribir_en_la_matriz(client, planta):
    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": NivelHabilidad.EXPERTO,
        },
        content_type="application/json",
    )

    assert respuesta.status_code in (401, 403)
    assert not SkillMatrix.objects.exists()


# --- CSRF: lo que la guía promete sobre Swagger y curl -------------------


def test_swagger_ui_deja_la_cookie_csrf(client):
    """La UI inyecta el token: sin cookie, el POST desde Swagger no funcionaría."""
    client.get(reverse("api:swagger-ui"))

    assert "csrftoken" in client.cookies


def test_post_con_sesion_sin_csrf_es_rechazado(usuario, planta):
    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(usuario)

    respuesta = cliente.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": NivelHabilidad.EXPERTO,
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 403
    assert not SkillMatrix.objects.exists()


def test_post_con_sesion_y_csrf_funciona(usuario, planta):
    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(usuario)
    cliente.get(reverse("api:swagger-ui"))  # deja la cookie csrftoken
    token = cliente.cookies["csrftoken"].value

    respuesta = cliente.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": NivelHabilidad.EXPERTO,
        },
        content_type="application/json",
        headers={"x-csrftoken": token},
    )

    assert respuesta.status_code == 200
    assert SkillMatrix.objects.get().nivel == "Experto"


def test_post_con_basic_auth_no_requiere_csrf(usuario, planta):
    """Por esto los ejemplos de curl de la guía usan `-u usuario:clave`."""
    credenciales = base64.b64encode(b"revisor:ClaveSegura123").decode()
    cliente = Client(enforce_csrf_checks=True)

    respuesta = cliente.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": NivelHabilidad.AUTONOMO,
        },
        content_type="application/json",
        headers={"authorization": f"Basic {credenciales}"},
    )

    assert respuesta.status_code == 200
    assert SkillMatrix.objects.get().nivel == "Autónomo"


# --- Compatibilidad con la ruta HTML ------------------------------------


def test_alias_html_sigue_funcionando(client, planta):
    """La ruta HTML mantiene la misma regla: solo el Jefe de Línea edita."""
    session = client.session
    session["empleado_id"] = planta["jefe"].pk
    session.save()

    respuesta = client.post(
        reverse("personal:actualizar_nivel_matriz"),
        data={
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": NivelHabilidad.AUTONOMO,
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"success": True, "nivel": "Autónomo"}
    assert SkillMatrix.objects.get().nivel == "Autónomo"
