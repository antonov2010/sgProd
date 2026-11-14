"""Pruebas de la conexión del tablero con la base de datos (US-13)."""

import pytest

from apps.calidad.models import Asignacion, RegistroCalidadHorario
from apps.dashboard.datos_reales import personal_real, registros_reales
from apps.dashboard.models import MetaEstacion
from apps.dashboard.tablero import construir_tablero
from apps.personal.models import Empleado, Estacion, Linea, Rol, SkillMatrix

pytestmark = pytest.mark.django_db


@pytest.fixture
def escenario():
    rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")
    rol_op = Rol.objects.create(nombre="Operador", tipo_rol="operador")
    linea = Linea.objects.create(nombre="Línea 3")
    jefe = Empleado.objects.create(numero_empleado="J1", nombre="Ana Jefa", rol=rol_jefe, linea=linea)
    linea.jefe_linea = jefe
    linea.save()
    op = Empleado.objects.create(numero_empleado="O1", nombre="Luis Operador", rol=rol_op, linea=linea)
    Empleado.objects.create(numero_empleado="O2", nombre="Baja Inactivo", rol=rol_op, linea=linea, activo=False)
    est = Estacion.objects.create(linea=linea, nombre="Soldadura", orden=1)
    MetaEstacion.objects.create(estacion=est, piezas_por_hora_meta=40)
    asig = Asignacion.objects.create(empleado=op, estacion=est, turno=1)
    for hora, (a, r, t) in {2: (38, 1, 1), 1: (40, 0, 0)}.items():
        RegistroCalidadHorario.objects.create(
            asignacion=asig, hora=hora, piezas_aceptadas=a, piezas_rechazadas=r, piezas_retrabajo=t
        )
    return linea


def test_sin_captura_devuelve_lista_vacia():
    assert registros_reales() == []


def test_registros_reales_tienen_la_forma_esperada_y_van_ordenados(escenario):
    regs = registros_reales()
    assert [r["hora"] for r in regs] == ["Hora 1", "Hora 2"]
    assert regs[0] == {
        "linea": "Línea 3", "estacion": "Soldadura", "turno": "Turno 1",
        "empleado": "Luis Operador", "hora": "Hora 1", "aceptadas": 40,
        "rechazadas": 0, "retrabajo": 0, "meta": 40,
    }


def test_estacion_sin_meta_usa_el_valor_por_defecto(escenario):
    MetaEstacion.objects.all().delete()
    assert {r["meta"] for r in registros_reales()} == {100}


def test_personal_real_solo_operadores_activos_y_jefe(escenario):
    assert personal_real() == {"Línea 3": {"jefe": "Ana Jefa", "operadores": ["Luis Operador"]}}


def test_el_tablero_se_arma_con_datos_reales(escenario):
    t = construir_tablero(registros_reales(), personal_real())
    assert len(t["lineas"]) == 1
    assert t["lineas"][0]["nombre"] == "Línea 3"
    assert t["lineas"][0]["personal"]["jefe"] == "Ana Jefa"
    assert t["empleados"][0]["nombre"] == "Luis Operador"


def test_el_desglose_por_turno_trae_las_claves_de_turno(escenario):
    """B-08: sin la clave ``turno`` el tablero dejaba ``por_turno`` vacío."""
    tablero = construir_tablero(registros_reales(), personal_real())
    assert set(tablero["por_turno"]) == {"Turno 1"}
    # 78 aceptadas de 80 piezas: FPY 97.5 % y 1.2 % de defectos.
    assert tablero["por_turno"]["Turno 1"]["fpy"] == 97.5
    assert tablero["por_turno"]["Turno 1"]["tasa_defectos"] == 1.2


def test_la_pantalla_del_gerente_muestra_la_seccion_por_turno(
    client, escenario, entrar
):
    entrar("gerente")
    html = client.get("/dashboard/gerente/").content.decode()
    assert "Por turno" in html
    assert "Turno 1" in html
    assert 'aria-label="Indicadores de FPY y tasa de defectos por turno"' in html


def test_sin_captura_la_seccion_por_turno_no_se_dibuja(client, entrar):
    entrar("gerente")
    respuesta = client.get("/dashboard/gerente/")
    assert respuesta.context["tablero"]["por_turno"] == {}
    assert "Por turno" not in respuesta.content.decode()


def test_la_pantalla_usa_ejemplo_si_no_hay_captura(client, entrar):
    entrar("gerente")
    r = client.get("/dashboard/gerente/")
    assert r.status_code == 200
    assert r.context["tablero_es_ejemplo"] is True
    assert "Datos de ejemplo" in r.content.decode()


def test_la_pantalla_usa_datos_reales_si_hay_captura(client, escenario, entrar):
    entrar("gerente")
    r = client.get("/dashboard/gerente/")
    assert r.context["tablero_es_ejemplo"] is False
    assert "Datos reales" in r.content.decode()


def test_personal_real_solo_cuenta_operadores_de_su_linea(escenario):
    """Ubicar al personal sale de Empleado.linea; la matriz no infla el conteo."""
    rol_op = Rol.objects.get(tipo_rol="operador")
    sin_linea = Empleado.objects.create(numero_empleado="O3", nombre="Sofia Matriz", rol=rol_op)
    SkillMatrix.objects.create(
        empleado=sin_linea, estacion=Estacion.objects.get(nombre="Soldadura"), nivel="Experto"
    )
    assert personal_real()["Línea 3"]["operadores"] == ["Luis Operador"]


def test_personal_real_sin_jefe_de_linea_no_falla(escenario):
    Linea.objects.update(jefe_linea=None)
    Empleado.objects.filter(numero_empleado="J1").update(linea=None)
    assert personal_real()["Línea 3"]["jefe"] == ""
