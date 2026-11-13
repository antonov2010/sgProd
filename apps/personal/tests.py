"""Pruebas de US-05 y de la corrección de US-06 (RF-1.1 y RF-1.2)."""

import json
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from . import services
from .models import Empleado, Estacion, Linea, NivelHabilidad, Rol, SkillMatrix

User = get_user_model()

PERMISOS_DE_CONSULTA = (
    "view_empleado",
    "view_estacion",
    "view_linea",
    "view_skillmatrix",
)


@pytest.fixture
def planta(db):
    """Dos líneas, dos jefes potenciales y personal en cada línea."""
    rol_operador = Rol.objects.create(nombre="Operador", tipo_rol="operador")
    rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")

    linea_3 = Linea.objects.create(nombre="Línea 3")
    linea_4 = Linea.objects.create(nombre="Línea 4")

    estacion_3 = Estacion.objects.create(linea=linea_3, nombre="Corte", orden=1)
    estacion_4 = Estacion.objects.create(linea=linea_4, nombre="Soldadura", orden=1)

    jefe_3 = Empleado.objects.create(
        numero_empleado="SG-0002",
        nombre="Rocío Salas",
        rol=rol_jefe,
        linea=linea_3,
    )
    linea_3.jefe_linea = jefe_3
    linea_3.save(update_fields=["jefe_linea"])

    ana = Empleado.objects.create(
        numero_empleado="SG-0100",
        nombre="Ana Activa",
        rol=rol_operador,
        linea=linea_3,
    )
    beto = Empleado.objects.create(
        numero_empleado="SG-0101",
        nombre="Beto Baja",
        rol=rol_operador,
        linea=linea_3,
        activo=False,
    )
    carla = Empleado.objects.create(
        numero_empleado="SG-0102",
        nombre="Carla Otra Línea",
        rol=rol_operador,
        linea=linea_4,
    )

    SkillMatrix.objects.create(
        empleado=ana, estacion=estacion_3, nivel=NivelHabilidad.EXPERTO
    )
    SkillMatrix.objects.create(
        empleado=carla, estacion=estacion_4, nivel=NivelHabilidad.AUTONOMO
    )

    return SimpleNamespace(
        linea_3=linea_3,
        linea_4=linea_4,
        estacion_3=estacion_3,
        estacion_4=estacion_4,
        jefe_3=jefe_3,
        ana=ana,
        beto=beto,
        carla=carla,
    )


def crear_usuario(username, *, superusuario=False, grupos=()):
    """Crea el usuario de Django que usa el Admin, con permiso de consulta."""
    usuario = User.objects.create_user(
        username=username,
        password="clave-de-prueba",
        is_staff=True,
        is_superuser=superusuario,
    )
    if not superusuario:
        usuario.user_permissions.set(
            Permission.objects.filter(codename__in=PERMISOS_DE_CONSULTA)
        )
    for nombre in grupos:
        grupo, _ = Group.objects.get_or_create(name=nombre)
        usuario.groups.add(grupo)
    return usuario


def test_admin_empleado_muestra_numero_nombre_y_estado(planta, client):
    client.force_login(crear_usuario("admin", superusuario=True))

    respuesta = client.get(reverse("admin:personal_empleado_changelist"))

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "SG-0100" in contenido
    assert "Ana Activa" in contenido
    assert "field-activo" in contenido
    assert "Línea 3" in contenido


def test_jefe_de_linea_solo_ve_al_personal_de_su_linea(planta, client):
    client.force_login(crear_usuario("jefe-linea-3", grupos=["Línea 3"]))

    contenido = client.get(
        reverse("admin:personal_empleado_changelist")
    ).content.decode()

    assert "SG-0100" in contenido
    assert "SG-0101" not in contenido
    assert "SG-0102" not in contenido


def test_jefe_de_linea_solo_ve_las_estaciones_de_su_linea(planta, client):
    client.force_login(crear_usuario("jefe-linea-3", grupos=["Línea 3"]))

    contenido = client.get(
        reverse("admin:personal_estacion_changelist")
    ).content.decode()

    assert "Corte" in contenido
    assert "Línea 3" in contenido
    assert "Soldadura" not in contenido
    assert "Línea 4" not in contenido


def test_jefe_de_linea_solo_ve_su_linea(planta, client):
    client.force_login(crear_usuario("jefe-linea-3", grupos=["Línea 3"]))

    contenido = client.get(reverse("admin:personal_linea_changelist")).content.decode()

    assert "Línea 3" in contenido
    assert "Línea 4" not in contenido
    assert "Rocío Salas" in contenido


def test_jefe_de_linea_solo_ve_su_matriz_de_habilidades(planta, client):
    client.force_login(crear_usuario("jefe-linea-3", grupos=["Línea 3"]))

    contenido = client.get(
        reverse("admin:personal_skillmatrix_changelist")
    ).content.decode()

    assert "Ana Activa" in contenido
    assert "Corte" in contenido
    assert "Carla Otra Línea" not in contenido
    assert "Soldadura" not in contenido


def test_superusuario_ve_toda_la_matriz(planta, client):
    client.force_login(crear_usuario("admin", superusuario=True))

    contenido = client.get(
        reverse("admin:personal_skillmatrix_changelist")
    ).content.decode()

    assert "Ana Activa" in contenido
    assert "Carla Otra Línea" in contenido


def test_superusuario_ve_todas_las_estaciones(planta, client):
    client.force_login(crear_usuario("admin", superusuario=True))

    contenido = client.get(
        reverse("admin:personal_estacion_changelist")
    ).content.decode()

    assert "Corte" in contenido
    assert "Soldadura" in contenido


def test_usuario_sin_linea_asignada_no_ve_datos_de_planta(planta, client):
    client.force_login(crear_usuario("sin-linea"))

    estaciones = client.get(
        reverse("admin:personal_estacion_changelist")
    ).content.decode()
    empleados = client.get(
        reverse("admin:personal_empleado_changelist")
    ).content.decode()
    habilidades = client.get(
        reverse("admin:personal_skillmatrix_changelist")
    ).content.decode()

    assert "Corte" not in estaciones
    assert "Soldadura" not in estaciones
    assert "Ana Activa" not in empleados
    assert "Carla Otra Línea" not in empleados
    assert "Ana Activa" not in habilidades
    assert "Carla Otra Línea" not in habilidades


def test_admin_linea_muestra_al_jefe_en_el_formulario(planta, client):
    client.force_login(crear_usuario("admin", superusuario=True))

    contenido = client.get(
        reverse("admin:personal_linea_change", args=[planta.linea_3.pk])
    ).content.decode()

    assert "Rocío Salas" in contenido


def test_linea_rechaza_como_jefe_a_quien_no_tiene_ese_rol(planta):
    planta.linea_3.jefe_linea = planta.ana

    with pytest.raises(ValidationError, match="Jefe de Línea"):
        planta.linea_3.full_clean()


class MatrizSeguridadTests(TestCase):
    def setUp(self):
        self.rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")
        self.rol_operador = Rol.objects.create(nombre="Operador", tipo_rol="operador")

        self.linea_3 = Linea.objects.create(nombre="Línea 3")
        self.linea_4 = Linea.objects.create(nombre="Línea 4")

        self.estacion_l3 = Estacion.objects.create(linea=self.linea_3, nombre="Corte", orden=1)
        self.estacion_l4 = Estacion.objects.create(linea=self.linea_4, nombre="Soldadura", orden=1)

        self.jefe_l3 = Empleado.objects.create(
            numero_empleado="SG-0003",
            nombre="Jefe L3",
            pin="123456",
            rol=self.rol_jefe,
            linea=self.linea_3,
            activo=True,
        )
        self.operador_l3 = Empleado.objects.create(
            numero_empleado="SG-0101",
            nombre="Operador L3",
            pin="123456",
            rol=self.rol_operador,
            linea=self.linea_3,
            activo=True,
        )
        self.operador_l4 = Empleado.objects.create(
            numero_empleado="SG-0201",
            nombre="Operador L4",
            pin="123456",
            rol=self.rol_operador,
            linea=self.linea_4,
            activo=True,
        )

    def test_anonimo_redirige_a_login_en_matriz(self):
        resp = self.client.get(reverse("personal:matriz_competencias"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("personal:login"))

    def test_anonimo_recibe_403_al_actualizar_nivel(self):
        resp = self.client.post(
            reverse("personal:actualizar_nivel_matriz"),
            data=json.dumps({
                "empleado_id": self.operador_l3.id,
                "estacion_id": self.estacion_l3.id,
                "nivel": "Principiante",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(SkillMatrix.objects.count(), 0)

    def test_operador_no_accede_a_matriz_ni_edita(self):
        session = self.client.session
        session["empleado_id"] = self.operador_l3.id
        session.save()

        resp_get = self.client.get(reverse("personal:matriz_competencias"))
        self.assertEqual(resp_get.status_code, 302)

        resp_post = self.client.post(
            reverse("personal:actualizar_nivel_matriz"),
            data=json.dumps({
                "empleado_id": self.operador_l3.id,
                "estacion_id": self.estacion_l3.id,
                "nivel": "Experto",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp_post.status_code, 403)
        self.assertEqual(SkillMatrix.objects.count(), 0)

    def test_jefe_no_puede_editar_otra_linea(self):
        session = self.client.session
        session["empleado_id"] = self.jefe_l3.id
        session.save()

        resp = self.client.post(
            reverse("personal:actualizar_nivel_matriz"),
            data=json.dumps({
                "empleado_id": self.operador_l4.id,
                "estacion_id": self.estacion_l4.id,
                "nivel": "Experto",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(SkillMatrix.objects.count(), 0)

    def test_servicio_rechaza_empleado_de_otra_linea(self):
        with self.assertRaises(services.NivelInvalido):
            services.actualizar_nivel(
                self.operador_l4.id,
                self.estacion_l3.id,
                "Experto",
                linea=self.linea_3,
            )