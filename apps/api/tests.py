"""Pruebas de la API REST y de su documentación Swagger.

Cubren lo que puede romperse sin que se note: que el esquema OpenAPI se
genere, que la UI de Swagger cargue, que la API exija autenticación y que el
POST de la matriz se comporte igual por la ruta REST y por la ruta HTML.
"""

import base64

import pytest
import yaml
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.personal.models import Empleado, Estacion, Linea, NivelHabilidad, Rol, SkillMatrix

User = get_user_model()


def crear_empleado(**datos):
    """Crea un empleado con el PIN ya hasheado (nunca en texto plano)."""
    pin = datos.pop("pin", None)
    empleado = Empleado.objects.create(**datos)
    if pin is not None:
        empleado.set_pin(pin)
        empleado.save(update_fields=["pin_hash"])
    return empleado


def crear_usuario(username, *, superusuario=False, grupos=()):
    """Usuario de Django con los grupos de línea que definen su alcance."""
    usuario = User.objects.create_user(
        username=username,
        password="ClaveSegura123",
        is_staff=True,
        is_superuser=superusuario,
    )
    for nombre in grupos:
        grupo, _ = Group.objects.get_or_create(name=nombre)
        usuario.groups.add(grupo)
    return usuario


@pytest.fixture
def usuario(db):
    """Staff con el grupo de la línea 3: el alcance mínimo para editar."""
    return crear_usuario("revisor", grupos=["Línea 3"])


@pytest.fixture
def usuario_sin_linea(db):
    return crear_usuario("sin-linea")


@pytest.fixture
def superusuario(db):
    return crear_usuario("superadmin", superusuario=True)


@pytest.fixture
def planta(db):
    rol = Rol.objects.create(nombre="Operador", tipo_rol="operador")
    rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")
    linea = Linea.objects.create(nombre="Línea 3")
    linea_4 = Linea.objects.create(nombre="Línea 4")
    estacion = Estacion.objects.create(linea=linea, nombre="Corte", orden=1)
    estacion_4 = Estacion.objects.create(linea=linea_4, nombre="Soldadura", orden=1)
    empleado = crear_empleado(
        numero_empleado="SG-0100",
        nombre="Ana Activa",
        pin="1234",
        rol=rol,
        linea=linea,
    )
    empleado_4 = crear_empleado(
        numero_empleado="SG-0102",
        nombre="Carla Otra Línea",
        pin="1234",
        rol=rol,
        linea=linea_4,
    )
    jefe = crear_empleado(
        numero_empleado="SG-0002",
        nombre="Rocío Salas",
        pin="1234",
        rol=rol_jefe,
        linea=linea,
    )
    return {
        "linea": linea,
        "linea_4": linea_4,
        "estacion": estacion,
        "estacion_4": estacion_4,
        "empleado": empleado,
        "empleado_4": empleado_4,
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
    datos = respuesta.json()["results"][0]
    assert "pin" not in datos
    assert "pin_hash" not in datos


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


# --- B-03: el POST respeta la línea del usuario --------------------------


def test_staff_con_grupo_linea_3_edita_una_estacion_de_su_linea(client, usuario, planta):
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
    assert SkillMatrix.objects.get().nivel == "Experto"


def test_staff_con_grupo_linea_3_no_edita_una_estacion_de_linea_4(client, usuario, planta):
    client.force_login(usuario)

    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado_4"].pk,
            "estacion_id": planta["estacion_4"].pk,
            "nivel": NivelHabilidad.EXPERTO,
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 403
    assert "otra línea" in respuesta.json()["error"]
    assert not SkillMatrix.objects.exists()


def test_staff_con_grupo_no_cruza_empleado_y_estacion_de_lineas_distintas(
    client, usuario, planta
):
    """La regla exige que empleado y estación compartan la misma línea."""
    client.force_login(usuario)

    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion_4"].pk,
            "nivel": NivelHabilidad.EXPERTO,
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 403
    assert "misma línea" in respuesta.json()["error"]
    assert not SkillMatrix.objects.exists()


def test_usuario_sin_grupo_de_linea_recibe_403(client, usuario_sin_linea, planta):
    client.force_login(usuario_sin_linea)

    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado"].pk,
            "estacion_id": planta["estacion"].pk,
            "nivel": NivelHabilidad.EXPERTO,
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 403
    assert "línea asignada" in respuesta.json()["error"]
    assert not SkillMatrix.objects.exists()


def test_superusuario_edita_cualquier_linea(client, superusuario, planta):
    client.force_login(superusuario)

    respuesta = client.post(
        reverse("api:matriz-nivel"),
        {
            "empleado_id": planta["empleado_4"].pk,
            "estacion_id": planta["estacion_4"].pk,
            "nivel": NivelHabilidad.INSTRUCTOR,
        },
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    assert SkillMatrix.objects.get().nivel == "Instructor"


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
