"""Pruebas de US-11 · Captura horaria por estación en tableta (RF-2.1, RNF-2).

Las pruebas del motivo de defecto obligatorio (US-12, RF-2.2) viven en
``tests.py``; aquí la captura envía un motivo válido cuando hay Rechazadas.
"""

import datetime
import json
import re
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.personal.models import Empleado, Estacion, Linea, NivelHabilidad, Rol, SkillMatrix

from . import services
from .models import Asignacion, CatalogoDefecto, RegistroCalidadHorario

def crear_empleado(**datos):
    """Crea un empleado con el PIN ya hasheado (nunca en texto plano)."""
    pin = datos.pop("pin", None)
    empleado = Empleado.objects.create(**datos)
    if pin is not None:
        empleado.set_pin(pin)
        empleado.save(update_fields=["pin_hash"])
    return empleado


PIN = "123456"
HORA = 9  # 09:00, dentro del turno 1


@pytest.fixture(autouse=True)
def reloj_fijo(monkeypatch):
    """La captura depende de la hora actual; las pruebas la fijan a las 09:00."""
    monkeypatch.setattr(services, "hora_actual", lambda: HORA)


@pytest.fixture
def planta(db):
    """Línea 3 con 8 estaciones y un operador por estación; Línea 4 aparte."""
    defecto = CatalogoDefecto.objects.create(codigo="DEF-T", descripcion="Falta de estaño")
    rol_operador = Rol.objects.create(nombre="Operador", tipo_rol="operador")
    rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")

    linea = Linea.objects.create(nombre="Línea 3")
    otra_linea = Linea.objects.create(nombre="Línea 4")
    estaciones = [
        Estacion.objects.create(linea=linea, nombre=f"Estación {i}", orden=i) for i in range(1, 9)
    ]
    estacion_ajena = Estacion.objects.create(linea=otra_linea, nombre="Ajena", orden=1)

    jefe = crear_empleado(
        numero_empleado="SG-0002", nombre="Rocío Salas", pin=PIN, rol=rol_jefe, linea=linea
    )
    linea.jefe_linea = jefe
    linea.save(update_fields=["jefe_linea"])

    operadores = []
    for i, estacion in enumerate(estaciones, start=1):
        operador = crear_empleado(
            numero_empleado=f"SG-01{i:02d}",
            nombre=f"Operador {i}",
            pin=PIN,
            rol=rol_operador,
            linea=linea,
        )
        nivel = NivelHabilidad.PRINCIPIANTE if i == 1 else NivelHabilidad.EXPERTO
        SkillMatrix.objects.create(empleado=operador, estacion=estacion, nivel=nivel)
        operadores.append(operador)

    ajeno = crear_empleado(
        numero_empleado="SG-0200", nombre="Ajeno", pin=PIN, rol=rol_operador, linea=otra_linea
    )
    return {
        "linea": linea,
        "estaciones": estaciones,
        "operadores": operadores,
        "jefe": jefe,
        "estacion_ajena": estacion_ajena,
        "ajeno": ajeno,
        "defecto": defecto,
    }


def entrar(client, numero):
    client.post(reverse("personal:login"), {"numero_empleado": numero, "pin": PIN})


def confirmar_asignacion(client, planta, mapa=None, turno=None):
    """Confirma la propuesta de RF-1.3 desde la matriz (US-08).

    A diferencia del diseño anterior, confirmar ya persiste ``Asignacion`` en la
    base; la captura solo las lee.
    """
    if mapa is None:
        mapa = {}
    # El formulario real envía un select por estación; las pruebas pueden pasar
    # solo las estaciones que cambian y el resto conserva su operador.
    mapa = {
        **{
            str(estacion.id): str(operador.id)
            for estacion, operador in zip(planta["estaciones"], planta["operadores"])
        },
        **mapa,
    }
    datos = {"guardar_asignacion": "1"}
    if turno is not None:
        datos["turno"] = str(turno)
    datos.update(
        {
            f"estacion_{estacion_id}": empleado_id
            for estacion_id, empleado_id in mapa.items()
        }
    )
    return client.post(reverse("personal:matriz_competencias"), datos)


@pytest.fixture
def jefe_en_captura(client, planta):
    entrar(client, "SG-0002")
    confirmar_asignacion(client, planta)
    respuesta = client.get(reverse("calidad:captura"))
    assert respuesta.status_code == 200
    return client


def capturar(client, asignacion, hora=HORA, aceptadas=100, rechazadas=2, retrabajo=1):
    datos = {
        "asignacion_id": asignacion.id,
        "hora": hora,
        "aceptadas": aceptadas,
        "rechazadas": rechazadas,
        "retrabajo": retrabajo,
    }
    if rechazadas:  # US-12: motivo obligatorio cuando hay Rechazadas
        datos["defecto_id"] = CatalogoDefecto.objects.get(codigo="DEF-T").id
    return client.post(
        reverse("calidad:guardar_captura"), json.dumps(datos), content_type="application/json"
    )


# --- Acceso ----------------------------------------------------------------


def test_captura_exige_sesion_de_jefe(client, planta):
    respuesta = client.get(reverse("calidad:captura"))
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("personal:login")

    respuesta = client.post(
        reverse("calidad:guardar_captura"), "{}", content_type="application/json"
    )
    assert respuesta.status_code == 403


def test_operador_no_entra_a_la_captura(client, planta):
    entrar(client, "SG-0101")
    respuesta = client.get(reverse("calidad:captura"))
    assert respuesta.status_code == 302


# --- La línea asignada se vuelve capturable ---------------------------------


def test_la_asignacion_vigente_se_guarda_como_asignaciones_del_turno(client, planta):
    entrar(client, "SG-0002")
    assert confirmar_asignacion(client, planta).status_code == 302

    asignaciones = Asignacion.objects.filter(estacion__linea=planta["linea"], turno=1)
    assert asignaciones.count() == 8
    principiante = asignaciones.get(empleado=planta["operadores"][0])
    assert principiante.alerta_supervision is True
    assert asignaciones.filter(alerta_supervision=False).count() == 7


def test_abrir_la_captura_no_escribe_en_la_base(client, planta):
    """La captura es solo lectura: la asignación se persiste al confirmarla."""
    entrar(client, "SG-0002")
    respuesta = client.get(reverse("calidad:captura"))
    assert respuesta.status_code == 200
    assert Asignacion.objects.count() == 0


def test_la_pantalla_muestra_las_8_estaciones_con_su_operador(jefe_en_captura, planta):
    html = jefe_en_captura.get(reverse("calidad:captura")).content.decode()
    for estacion, operador in zip(planta["estaciones"], planta["operadores"]):
        assert estacion.nombre in html
        assert operador.nombre in html
    assert html.count("data-asignacion=") == 8


def test_un_operador_dado_de_baja_no_queda_asignado(client, planta):
    """La captura respeta el hook de asistencia (RF-1.4): solo personal presente."""
    baja = planta["operadores"][1]
    baja.activo = False
    baja.save(update_fields=["activo"])
    entrar(client, "SG-0002")
    confirmar_asignacion(client, planta)

    html = client.get(reverse("calidad:captura")).content.decode()
    assert not Asignacion.objects.filter(empleado=baja).exists()
    assert Asignacion.objects.filter(estacion__linea=planta["linea"]).count() == 7
    assert html.count("data-asignacion=") == 7
    assert "1 estación sin operador" in html


def test_dos_estaciones_sin_operador_usan_el_plural_correcto(client, planta):
    """B-14: con dos estaciones descubiertas se lee «2 estaciones», no «2 estaciónes»."""
    for operador in planta["operadores"][:2]:
        operador.activo = False
        operador.save(update_fields=["activo"])
    entrar(client, "SG-0002")
    confirmar_asignacion(client, planta)

    html = client.get(reverse("calidad:captura")).content.decode()
    assert "2 estaciones sin operador" in html
    assert "estaciónes" not in html


def test_cambiar_la_vigente_no_reescribe_una_estacion_ya_capturada(jefe_en_captura, planta):
    asignacion_1, asignacion_2 = Asignacion.objects.filter(
        estacion__in=planta["estaciones"][:2]
    ).order_by("estacion__orden")
    capturar(jefe_en_captura, asignacion_1)

    # El jefe intercambia a los operadores de las estaciones 1 y 2 al confirmar.
    estacion_1, estacion_2 = (str(e.id) for e in planta["estaciones"][:2])
    operador_1, operador_2 = (str(o.id) for o in planta["operadores"][:2])
    confirmar_asignacion(
        jefe_en_captura,
        planta,
        mapa={estacion_1: operador_2, estacion_2: operador_1},
    )
    jefe_en_captura.get(reverse("calidad:captura"))

    asignacion_1.refresh_from_db()
    asignacion_2.refresh_from_db()
    assert asignacion_1.empleado == planta["operadores"][0]  # ya tenía piezas: se conserva
    # El operador 1 no puede quedar en dos estaciones: la 2 conserva al suyo y
    # el conflicto se reporta al jefe.
    assert asignacion_2.empleado == planta["operadores"][1]
    assert (
        Asignacion.objects.filter(fecha=asignacion_1.fecha, turno=1)
        .values("empleado_id")
        .distinct()
        .count()
        == 8
    )


def test_limpiar_una_estacion_sin_piezas_borra_la_asignacion(jefe_en_captura, planta):
    """Descubrir una estación sin capturas elimina su asignación."""
    estacion = planta["estaciones"][0]
    asignacion = Asignacion.objects.get(estacion=estacion, turno=1)
    mapa = {
        str(est.id): str(op.id)
        for est, op in zip(planta["estaciones"], planta["operadores"])
    }
    mapa[str(estacion.id)] = ""

    confirmar_asignacion(jefe_en_captura, planta, mapa=mapa)

    assert not Asignacion.objects.filter(pk=asignacion.pk).exists()
    assert (
        Asignacion.objects.filter(
            estacion__linea=planta["linea"], turno=1
        ).count()
        == 7
    )


def test_doble_confirmacion_es_idempotente(client, planta):
    """Confirmar dos veces seguidas no duplica las asignaciones del turno."""
    entrar(client, "SG-0002")
    assert confirmar_asignacion(client, planta).status_code == 302
    assert confirmar_asignacion(client, planta).status_code == 302

    assert (
        Asignacion.objects.filter(
            estacion__linea=planta["linea"], turno=1
        ).count()
        == 8
    )


def test_la_asignacion_persiste_tras_cerrar_sesion(client, planta):
    """La asignación vive en la base: otro Client la ve sin heredar la sesión."""
    entrar(client, "SG-0002")
    confirmar_asignacion(client, planta)
    client.get(reverse("personal:logout"))

    otro = Client()
    entrar(otro, "SG-0002")
    html = otro.get(reverse("calidad:captura")).content.decode()
    assert html.count("data-asignacion=") == 8
    assert (
        Asignacion.objects.filter(
            estacion__linea=planta["linea"], turno=1
        ).count()
        == 8
    )


def test_la_confirmacion_y_la_tabla_usan_el_turno_del_formulario(client, planta):
    """El turno del hidden manda: no se vuelve a leer el reloj en la tabla."""
    entrar(client, "SG-0002")
    respuesta = confirmar_asignacion(client, planta, turno=2)

    assert respuesta.status_code == 302
    assert respuesta.url.endswith("?turno=2")
    assert (
        Asignacion.objects.filter(
            estacion__linea=planta["linea"], turno=2
        ).count()
        == 8
    )
    assert not Asignacion.objects.filter(turno=1).exists()

    tabla_turno_2 = client.get(
        reverse("personal:matriz_competencias") + "?turno=2"
    ).context["tabla_vigente_estatica"]
    assert all(item["empleado_asignado"] for item in tabla_turno_2)

    tabla_turno_1 = client.get(
        reverse("personal:matriz_competencias")
    ).context["tabla_vigente_estatica"]
    assert not any(item["empleado_asignado"] for item in tabla_turno_1)


def test_la_matriz_publica_los_datos_con_json_script(jefe_en_captura):
    """El script no recibe JSON interpolado ni nombres con |safe."""
    html = jefe_en_captura.get(
        reverse("personal:matriz_competencias") + "?sugerir=1&turno=1"
    ).content.decode()

    assert '<script id="mapa-niveles" type="application/json">' in html
    assert '<script id="instructores-apoyo" type="application/json">' in html
    assert 'name="turno" value="1"' in html
    assert "JSON.parse('" not in html


# --- Criterio 1: una hora completa en menos de 3 minutos (O2) ---------------


def test_registrar_una_hora_completa_de_8_estaciones(jefe_en_captura, planta):
    inicio = time.perf_counter()
    for asignacion in Asignacion.objects.filter(estacion__linea=planta["linea"]):
        assert capturar(jefe_en_captura, asignacion).status_code == 201
    assert time.perf_counter() - inicio < 180
    assert RegistroCalidadHorario.objects.filter(hora=HORA).count() == 8


# --- Criterio 2: cada captura responde en menos de 1.5 s (RNF-2) ------------


def test_cada_captura_responde_en_menos_de_1_5_segundos(jefe_en_captura, planta):
    asignacion = Asignacion.objects.filter(estacion__linea=planta["linea"]).first()
    inicio = time.perf_counter()
    respuesta = capturar(jefe_en_captura, asignacion)
    assert time.perf_counter() - inicio < 1.5
    assert respuesta.json()["ms"] < 1500


def test_guardar_otra_vez_la_misma_hora_corrige_sin_duplicar(jefe_en_captura, planta):
    asignacion = Asignacion.objects.filter(estacion__linea=planta["linea"]).first()
    assert capturar(jefe_en_captura, asignacion, aceptadas=100).status_code == 201
    respuesta = capturar(jefe_en_captura, asignacion, aceptadas=95)
    assert respuesta.status_code == 200
    registro = RegistroCalidadHorario.objects.get(asignacion=asignacion, hora=HORA)
    assert registro.piezas_aceptadas == 95


@pytest.mark.parametrize(
    "cambio",
    [{"aceptadas": -1}, {"rechazadas": "diez"}, {"retrabajo": 10000}, {"hora": 20}],
)
def test_rechaza_valores_invalidos(jefe_en_captura, planta, cambio):
    asignacion = Asignacion.objects.filter(estacion__linea=planta["linea"]).first()
    respuesta = capturar(jefe_en_captura, asignacion, **cambio)
    assert respuesta.status_code == 400
    assert respuesta.json()["error"]
    assert not RegistroCalidadHorario.objects.exists()


def test_no_captura_un_turno_ya_cerrado(jefe_en_captura, planta, monkeypatch):
    """B-06: con el reloj en turno 2 no se corrige una captura del turno 1."""
    monkeypatch.setattr(services, "hora_actual", lambda: 15)  # 15:00, turno 2
    asignacion = Asignacion.objects.filter(
        estacion__linea=planta["linea"], turno=1
    ).first()

    respuesta = capturar(jefe_en_captura, asignacion, hora=HORA)

    assert respuesta.status_code == 400
    assert (
        respuesta.json()["error"]
        == "Ese turno ya está cerrado; solo se captura el turno en curso."
    )
    assert not RegistroCalidadHorario.objects.exists()


def test_no_captura_estaciones_de_otra_linea(jefe_en_captura, planta):
    ajena = Asignacion.objects.create(
        empleado=planta["ajeno"], estacion=planta["estacion_ajena"], turno=1
    )
    respuesta = capturar(jefe_en_captura, ajena)
    assert respuesta.status_code == 400
    assert not RegistroCalidadHorario.objects.exists()


# --- Criterio 3: cada control tiene al menos 56 px -------------------------


def test_los_controles_tactiles_miden_al_menos_56_px():
    theme = (Path(settings.BASE_DIR) / "static/css/theme.css").read_text(encoding="utf-8")
    assert re.search(r"--sg-touch:\s*56px", theme)

    plantilla = (
        Path(__file__).parent / "templates/calidad/captura.html"
    ).read_text(encoding="utf-8")
    for selector in (".cap-horas a", ".cap-campo button", ".cap-campo input", ".cap-defecto select"):
        regla = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", plantilla).group(1)
        assert "min-height: var(--sg-touch)" in regla, selector


# --- Criterio 4: el registro de la hora anterior se consulta ---------------


def test_el_registro_de_la_hora_anterior_aparece_con_hora_estacion_y_valores(
    jefe_en_captura, planta
):
    asignacion = Asignacion.objects.filter(estacion=planta["estaciones"][2]).get()
    capturar(jefe_en_captura, asignacion, hora=8, aceptadas=117, rechazadas=4, retrabajo=3)

    html = jefe_en_captura.get(reverse("calidad:captura")).content.decode()
    fila = re.search(r'<tr data-registro="\d+">(.*?)</tr>', html, re.S).group(1)
    celdas = [
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
        for c in re.findall(r"<td[^>]*>(.*?)</td>", fila, re.S)
    ]
    assert celdas == [
        "08:00", "Estación 3", "Operador 3", "117", "4", "3", "DEF-T: Falta de estaño"
    ]


# --- Turnos ------------------------------------------------------------------


def test_el_turno_3_cruza_la_medianoche():
    assert services.horas_del_turno(3) == [22, 23, 0, 1, 2, 3, 4, 5]
    assert services.turno_de_la_hora(2) == 3
    assert services.turno_de_la_hora(6) == 1
    assert services.turno_de_la_hora(21) == 2


# --- B-05: el turno 3 pertenece a la fecha en que inicia la guardia ----------


@pytest.fixture
def madrugada_turno_3(monkeypatch):
    """Reloj de planta a las 00:30: la guardia del turno 3 empezó ayer."""
    monkeypatch.setattr(services, "hora_actual", lambda: 0)
    return timezone.localdate() - datetime.timedelta(days=1)


def test_a_las_00_30_la_asignacion_del_turno_3_usa_la_fecha_de_ayer(
    client, planta, madrugada_turno_3
):
    """La guardia que arrancó ayer a las 22:00 mantiene su fecha al confirmar."""
    entrar(client, "SG-0002")
    assert confirmar_asignacion(client, planta, turno=3).status_code == 302

    asignaciones = Asignacion.objects.filter(estacion__linea=planta["linea"], turno=3)
    assert asignaciones.count() == 8
    assert set(asignaciones.values_list("fecha", flat=True)) == {madrugada_turno_3}


def test_el_historial_del_turno_3_muestra_las_8_horas(planta, madrugada_turno_3):
    """22:00, 23:00 y 00:00–05:00 viven en la asignación del día anterior."""
    asignacion = Asignacion.objects.create(
        empleado=planta["operadores"][0],
        estacion=planta["estaciones"][0],
        turno=3,
        fecha=madrugada_turno_3,
    )
    for hora in services.horas_del_turno(3):
        RegistroCalidadHorario.objects.create(
            asignacion=asignacion, hora=hora, piezas_aceptadas=10
        )

    historial = services.historial_del_turno(planta["linea"], 3)

    assert len(historial) == 8
    assert {r.hora for r in historial} == set(services.horas_del_turno(3))


def test_a_las_00_30_la_captura_escribe_en_la_asignacion_de_ayer(
    client, planta, madrugada_turno_3
):
    """Capturar a las 00:30 usa la guardia de ayer y no crea una segunda fila."""
    entrar(client, "SG-0002")
    confirmar_asignacion(client, planta, turno=3)
    asignacion = Asignacion.objects.get(estacion=planta["estaciones"][0], turno=3)

    respuesta = capturar(client, asignacion, hora=0)

    assert respuesta.status_code == 201
    registro = RegistroCalidadHorario.objects.get(asignacion=asignacion, hora=0)
    assert registro.piezas_aceptadas == 100
    assert (
        Asignacion.objects.filter(
            estacion=planta["estaciones"][0], fecha=madrugada_turno_3, turno=3
        ).count()
        == 1
    )
    assert Asignacion.objects.filter(turno=3).count() == 8


def test_a_las_00_30_el_turno_2_de_ayer_sigue_cerrado(
    client, planta, madrugada_turno_3
):
    """B-06 compara contra la fecha de la guardia, no contra la fecha de hoy."""
    entrar(client, "SG-0002")
    turno_2 = Asignacion.objects.create(
        empleado=planta["operadores"][0],
        estacion=planta["estaciones"][0],
        turno=2,
        fecha=madrugada_turno_3,
    )

    respuesta = capturar(client, turno_2, hora=21)

    assert respuesta.status_code == 400
    assert (
        respuesta.json()["error"]
        == "Ese turno ya está cerrado; solo se captura el turno en curso."
    )
    assert not RegistroCalidadHorario.objects.exists()


# --- Fecha de planta -----------------------------------------------------------
# La fecha de una asignación debe salir de TIME_ZONE (America/Tijuana), no del
# reloj del sistema: en Windows, con TZ en el .env, date.today() da la fecha UTC
# y por la tarde ya es el día siguiente. Se simula un "ahora" que nunca coincide
# con el reloj real (19:30 en Tijuana del 15-ene-2030 = 03:30 UTC del 16), así la
# prueba falla si algo vuelve a usar date.today() / auto_now_add.
TARDE_EN_PLANTA = datetime.datetime(2030, 1, 16, 3, 30, tzinfo=datetime.timezone.utc)


@pytest.fixture
def tarde_en_planta(monkeypatch):
    monkeypatch.setattr(services, "hora_actual", lambda: 19)
    with patch.object(timezone, "now", return_value=TARDE_EN_PLANTA):
        yield datetime.date(2030, 1, 15)


def test_la_asignacion_usa_la_fecha_de_planta_y_no_la_utc(client, planta, tarde_en_planta):
    entrar(client, "SG-0002")
    confirmar_asignacion(client, planta)

    fechas = set(Asignacion.objects.values_list("fecha", flat=True))
    assert fechas == {tarde_en_planta}


def test_por_la_tarde_se_captura_sin_duplicar_asignaciones(client, planta, tarde_en_planta):
    entrar(client, "SG-0002")
    confirmar_asignacion(client, planta)
    asignacion = Asignacion.objects.filter(estacion__linea=planta["linea"]).first()

    assert capturar(client, asignacion, hora=19).status_code == 201
    client.get(reverse("calidad:captura"))  # volver a abrir la pantalla
    assert Asignacion.objects.filter(estacion__linea=planta["linea"]).count() == 8


def test_la_fecha_por_defecto_del_modelo_es_la_de_planta(planta, tarde_en_planta):
    asignacion = Asignacion.objects.create(
        empleado=planta["operadores"][0], estacion=planta["estaciones"][0], turno=2
    )
    assert asignacion.fecha == tarde_en_planta
