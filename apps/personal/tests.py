"""Pruebas de US-05 y de la corrección de US-06 (RF-1.1 y RF-1.2)."""

import json
import re
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.calidad.models import Asignacion

from . import services
from .models import Empleado, Estacion, Linea, NivelHabilidad, Rol, SkillMatrix
from .views import MAX_INTENTOS_FALLIDOS, MENSAJE_BLOQUEO

User = get_user_model()


def crear_empleado(**datos):
    """Crea un empleado con el PIN ya hasheado (nunca en texto plano)."""
    pin = datos.pop("pin", None)
    empleado = Empleado.objects.create(**datos)
    if pin is not None:
        empleado.set_pin(pin)
        empleado.save(update_fields=["pin_hash"])
    return empleado


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

    jefe_3 = crear_empleado(
        numero_empleado="SG-0002",
        nombre="Rocío Salas",
        rol=rol_jefe,
        linea=linea_3,
    )
    linea_3.jefe_linea = jefe_3
    linea_3.save(update_fields=["jefe_linea"])

    ana = crear_empleado(
        numero_empleado="SG-0100",
        nombre="Ana Activa",
        rol=rol_operador,
        linea=linea_3,
    )
    beto = crear_empleado(
        numero_empleado="SG-0101",
        nombre="Beto Baja",
        rol=rol_operador,
        linea=linea_3,
        activo=False,
    )
    carla = crear_empleado(
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

        self.jefe_l3 = crear_empleado(
            numero_empleado="SG-0003",
            nombre="Jefe L3",
            pin="123456",
            rol=self.rol_jefe,
            linea=self.linea_3,
            activo=True,
        )
        self.operador_l3 = crear_empleado(
            numero_empleado="SG-0101",
            nombre="Operador L3",
            pin="123456",
            rol=self.rol_operador,
            linea=self.linea_3,
            activo=True,
        )
        self.operador_l4 = crear_empleado(
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

    def _post_json(self, cuerpo):
        session = self.client.session
        session["empleado_id"] = self.jefe_l3.id
        session.save()
        return self.client.post(
            reverse("personal:actualizar_nivel_matriz"),
            data=json.dumps(cuerpo),
            content_type="application/json",
        )

    def test_b07_cuerpo_lista_no_devuelve_500_en_matriz(self):
        respuesta = self._post_json([])

        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()["success"])

    def test_b07_cuerpo_null_no_devuelve_500_en_matriz(self):
        respuesta = self._post_json(None)

        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()["success"])

    def test_b07_ids_no_numericos_no_devuelven_500_en_matriz(self):
        respuesta = self._post_json(
            {"empleado_id": "abc", "estacion_id": "x", "nivel": "Experto"}
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("empleado_id", respuesta.json()["error"])
        self.assertEqual(SkillMatrix.objects.count(), 0)

    def test_b07_falta_nivel_no_devuelve_500_en_matriz(self):
        respuesta = self._post_json(
            {"empleado_id": self.operador_l3.id, "estacion_id": self.estacion_l3.id}
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("nivel", respuesta.json()["error"])
        self.assertEqual(SkillMatrix.objects.count(), 0)


class MatrizFiltrosTests(TestCase):
    """Lote C: filtros de la matriz general y guardado con filtros activos."""

    def setUp(self):
        self.rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")
        self.rol_operador = Rol.objects.create(nombre="Operador", tipo_rol="operador")
        self.linea = Linea.objects.create(nombre="Línea 3")
        self.corte = Estacion.objects.create(linea=self.linea, nombre="Corte", orden=1)
        self.soldadura = Estacion.objects.create(
            linea=self.linea, nombre="Soldadura", orden=2
        )

        self.jefe = crear_empleado(
            numero_empleado="SG-0003",
            nombre="Jefe L3",
            rol=self.rol_jefe,
            linea=self.linea,
            activo=True,
        )
        self.ana = crear_empleado(
            numero_empleado="SG-0101",
            nombre="Ana López",
            rol=self.rol_operador,
            linea=self.linea,
            activo=True,
        )
        self.bruno = crear_empleado(
            numero_empleado="SG-0102",
            nombre="Bruno Díaz",
            rol=self.rol_operador,
            linea=self.linea,
            activo=True,
        )
        self.carla = crear_empleado(
            numero_empleado="SG-0103",
            nombre="Carla Ruiz",
            rol=self.rol_operador,
            linea=self.linea,
            activo=True,
        )

        # Ana y Carla tienen nivel en todas las estaciones; a Bruno le falta una.
        for estacion in (self.corte, self.soldadura):
            SkillMatrix.objects.create(
                empleado=self.ana, estacion=estacion, nivel=NivelHabilidad.EXPERTO
            )
            SkillMatrix.objects.create(
                empleado=self.carla, estacion=estacion, nivel=NivelHabilidad.AUTONOMO
            )
        SkillMatrix.objects.create(
            empleado=self.bruno,
            estacion=self.corte,
            nivel=NivelHabilidad.PRINCIPIANTE,
        )

        sesion = self.client.session
        sesion["empleado_id"] = self.jefe.id
        sesion.save()

        self.url = reverse("personal:matriz_competencias")

    def _nombres_mostrados(self, respuesta):
        return [fila["empleado"].nombre for fila in respuesta.context["matriz"]]

    def test_filtro_q_busca_por_nombre(self):
        respuesta = self.client.get(self.url, {"q": "ANA"})

        self.assertEqual(self._nombres_mostrados(respuesta), ["Ana López"])

    def test_filtro_q_busca_por_numero_empleado(self):
        respuesta = self.client.get(self.url, {"q": "sg-0102"})

        self.assertEqual(self._nombres_mostrados(respuesta), ["Bruno Díaz"])

    def test_filtro_faltantes_solo_operadores_con_estacion_sin_nivel(self):
        respuesta = self.client.get(self.url, {"faltantes": "1"})

        self.assertEqual(self._nombres_mostrados(respuesta), ["Bruno Díaz"])

    def test_resumen_muestra_el_total_sin_filtrar(self):
        respuesta = self.client.get(self.url, {"q": "Bruno"})

        self.assertContains(respuesta, "Mostrando 1 de 3 operadores")

    def test_vista_asignacion_no_renderiza_la_tabla_de_habilidades(self):
        respuesta = self.client.get(self.url, {"vista": "asignacion"})

        self.assertEqual(respuesta.context["vista"], "asignacion")
        self.assertContains(respuesta, "Asignación vigente de la línea en el turno")
        self.assertNotContains(
            respuesta, "Matriz general de habilidades por operador y estación."
        )

    def test_vista_matriz_no_renderiza_la_tabla_de_asignacion(self):
        respuesta = self.client.get(self.url, {"vista": "matriz"})

        self.assertEqual(respuesta.context["vista"], "matriz")
        self.assertContains(
            respuesta, "Matriz general de habilidades por operador y estación."
        )
        self.assertNotContains(
            respuesta, "Asignación vigente de la línea en el turno"
        )

    def test_vista_invalida_cae_en_la_matriz(self):
        respuesta = self.client.get(self.url, {"vista": "otra"})

        self.assertEqual(respuesta.context["vista"], "matriz")
        self.assertContains(
            respuesta, "Matriz general de habilidades por operador y estación."
        )
        self.assertNotContains(
            respuesta, "Asignación vigente de la línea en el turno"
        )

    def test_pestanas_conservan_q_faltantes_y_turno(self):
        respuesta = self.client.get(
            self.url, {"q": "ana", "faltantes": "1", "turno": "2"}
        )
        contenido = respuesta.content.decode()

        self.assertContains(respuesta, 'role="tablist"')
        self.assertEqual(contenido.count('role="tab"'), 2)

        for vista in ("matriz", "asignacion"):
            enlaces = re.findall(
                rf'href="([^"]*vista={vista}[^"]*)"', contenido
            )
            self.assertTrue(enlaces, f"Falta la pestaña {vista}")
            for enlace in enlaces:
                self.assertIn("q=ana", enlace)
                self.assertIn("faltantes=1", enlace)
                self.assertIn("turno=2", enlace)

    def test_mostrando_x_de_y_sigue_apareciendo_y_el_filtro_es_buscable(self):
        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, "Mostrando 3 de 3 operadores")
        self.assertContains(respuesta, 'aria-live="polite"')
        self.assertContains(respuesta, 'type="search"')
        self.assertContains(respuesta, 'autocomplete="off"')
        self.assertContains(respuesta, 'for="filtro-q"')
        self.assertContains(respuesta, 'id="filtro-q"')

    def test_guardar_asignacion_con_filtros_activos_guarda_todas_las_estaciones(self):
        respuesta = self.client.post(
            f"{self.url}?q=ana&faltantes=1&turno=2",
            {
                "guardar_asignacion": "1",
                "turno": "2",
                f"estacion_{self.corte.id}": str(self.ana.id),
                f"estacion_{self.soldadura.id}": str(self.bruno.id),
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        asignaciones = Asignacion.objects.filter(turno=2)
        self.assertEqual(asignaciones.count(), 2)
        self.assertSetEqual(
            set(asignaciones.values_list("estacion_id", flat=True)),
            {self.corte.id, self.soldadura.id},
        )


class PinHasheadoTests(TestCase):
    """B-01: el PIN de planta se guarda y se valida siempre como hash."""

    def setUp(self):
        self.rol = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")
        self.linea = Linea.objects.create(nombre="Línea 3")
        self.empleado = crear_empleado(
            numero_empleado="SG-0002",
            nombre="Rocío Salas",
            pin="123456",
            rol=self.rol,
            linea=self.linea,
        )

    def test_pin_no_se_guarda_en_texto_plano(self):
        self.empleado.refresh_from_db()

        self.assertNotEqual(self.empleado.pin_hash, "123456")
        self.assertTrue(self.empleado.check_pin("123456"))

    def test_check_pin_acepta_el_correcto_y_rechaza_el_incorrecto(self):
        self.assertTrue(self.empleado.check_pin("123456"))
        self.assertFalse(self.empleado.check_pin("654321"))

    def test_check_pin_tolera_un_empleado_sin_pin(self):
        self.empleado.pin_hash = None

        self.assertFalse(self.empleado.check_pin("123456"))

    def test_login_funciona_con_el_pin_hasheado(self):
        respuesta = self.client.post(
            reverse("personal:login"),
            {"numero_empleado": "SG-0002", "pin": "123456"},
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.client.session["empleado_id"], self.empleado.id)


class BloqueoPorIntentosTests(TestCase):
    """B-02: cinco fallos bloquean el acceso temporalmente, sin perder el motivo."""

    def setUp(self):
        # La cache local sobrevive entre pruebas: se limpia antes y después.
        cache.clear()
        self.addCleanup(cache.clear)
        self.rol = Rol.objects.create(nombre="Operador", tipo_rol="operador")
        self.empleado = crear_empleado(
            numero_empleado="SG-0002",
            nombre="Rocío Salas",
            pin="123456",
            rol=self.rol,
        )
        self.url = reverse("personal:login")

    def _intentar(self, pin):
        return self.client.post(
            self.url,
            {"numero_empleado": "SG-0002", "pin": pin},
        )

    def test_cinco_fallos_bloquean_incluso_el_pin_correcto(self):
        respuesta = self._intentar("000000")
        self.assertContains(respuesta, "PIN incorrecto")

        for _ in range(MAX_INTENTOS_FALLIDOS - 1):
            respuesta = self._intentar("000000")

        self.assertContains(respuesta, MENSAJE_BLOQUEO)
        respuesta = self._intentar("123456")
        self.assertContains(respuesta, MENSAJE_BLOQUEO)
        self.assertNotIn("empleado_id", self.client.session)

    def test_al_terminar_el_bloqueo_vuelve_a_entrar(self):
        for _ in range(MAX_INTENTOS_FALLIDOS):
            self._intentar("000000")

        self.assertContains(self._intentar("123456"), MENSAJE_BLOQUEO)
        cache.clear()  # simula que expiró la ventana de 15 minutos

        respuesta = self._intentar("123456")
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.client.session["empleado_id"], self.empleado.id)

    def test_un_login_correcto_limpia_el_contador(self):
        for _ in range(MAX_INTENTOS_FALLIDOS - 1):
            self._intentar("000000")
        self.assertEqual(self._intentar("123456").status_code, 302)

        for _ in range(MAX_INTENTOS_FALLIDOS - 1):
            respuesta = self._intentar("000000")

        self.assertContains(respuesta, "PIN incorrecto")
        self.assertNotContains(respuesta, MENSAJE_BLOQUEO)
