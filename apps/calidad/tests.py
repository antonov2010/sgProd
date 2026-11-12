"""Pruebas de US-11 · Captura horaria por estación en tableta (RF-2.1, RNF-2)."""

import json
import re
import time
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from apps.personal.models import Empleado, Estacion, Linea, NivelHabilidad, Rol, SkillMatrix

from . import services
from .models import Asignacion, RegistroCalidadHorario

PIN = "123456"
HORA = 9  # 09:00, dentro del turno 1


@pytest.fixture(autouse=True)
def reloj_fijo(monkeypatch):
    """La captura depende de la hora actual; las pruebas la fijan a las 09:00."""
    monkeypatch.setattr(services, "hora_actual", lambda: HORA)


@pytest.fixture
def planta(db):
    """Línea 3 con 8 estaciones y un operador por estación; Línea 4 aparte."""
    rol_operador = Rol.objects.create(nombre="Operador", tipo_rol="operador")
    rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")

    linea = Linea.objects.create(nombre="Línea 3")
    otra_linea = Linea.objects.create(nombre="Línea 4")
    estaciones = [
        Estacion.objects.create(linea=linea, nombre=f"Estación {i}", orden=i) for i in range(1, 9)
    ]
    estacion_ajena = Estacion.objects.create(linea=otra_linea, nombre="Ajena", orden=1)

    jefe = Empleado.objects.create(
        numero_empleado="SG-0002", nombre="Rocío Salas", pin=PIN, rol=rol_jefe, linea=linea
    )
    linea.jefe_linea = jefe
    linea.save(update_fields=["jefe_linea"])

    operadores = []
    for i, estacion in enumerate(estaciones, start=1):
        operador = Empleado.objects.create(
            numero_empleado=f"SG-01{i:02d}",
            nombre=f"Operador {i}",
            pin=PIN,
            rol=rol_operador,
            linea=linea,
        )
        nivel = NivelHabilidad.PRINCIPIANTE if i == 1 else NivelHabilidad.EXPERTO
        SkillMatrix.objects.create(empleado=operador, estacion=estacion, nivel=nivel)
        operadores.append(operador)

    ajeno = Empleado.objects.create(
        numero_empleado="SG-0200", nombre="Ajeno", pin=PIN, rol=rol_operador, linea=otra_linea
    )
    return {
        "linea": linea,
        "estaciones": estaciones,
        "operadores": operadores,
        "jefe": jefe,
        "estacion_ajena": estacion_ajena,
        "ajeno": ajeno,
    }


def entrar(client, numero):
    client.post(reverse("personal:login"), {"numero_empleado": numero, "pin": PIN})


def guardar_vigente(client, planta):
    """Simula la asignación vigente que guarda la matriz (RF-1.3) en la sesión."""
    session = client.session
    session[f"asignacion_vigente_{planta['linea'].id}"] = {
        str(e.id): str(o.id) for e, o in zip(planta["estaciones"], planta["operadores"])
    }
    session.save()


@pytest.fixture
def jefe_en_captura(client, planta):
    entrar(client, "SG-0002")
    guardar_vigente(client, planta)
    respuesta = client.get(reverse("calidad:captura"))
    assert respuesta.status_code == 200
    return client


def capturar(client, asignacion, hora=HORA, aceptadas=100, rechazadas=2, retrabajo=1):
    return client.post(
        reverse("calidad:guardar_captura"),
        json.dumps(
            {
                "asignacion_id": asignacion.id,
                "hora": hora,
                "aceptadas": aceptadas,
                "rechazadas": rechazadas,
                "retrabajo": retrabajo,
            }
        ),
        content_type="application/json",
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


def test_la_asignacion_vigente_se_guarda_como_asignaciones_del_turno(jefe_en_captura, planta):
    asignaciones = Asignacion.objects.filter(estacion__linea=planta["linea"], turno=1)
    assert asignaciones.count() == 8
    principiante = asignaciones.get(empleado=planta["operadores"][0])
    assert principiante.alerta_supervision is True
    assert asignaciones.filter(alerta_supervision=False).count() == 7


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
    guardar_vigente(client, planta)

    html = client.get(reverse("calidad:captura")).content.decode()
    assert not Asignacion.objects.filter(empleado=baja).exists()
    assert html.count("data-asignacion=") == 7
    assert "1 estación sin operador" in html


def test_cambiar_la_vigente_no_reescribe_una_estacion_ya_capturada(jefe_en_captura, planta):
    asignacion_1, asignacion_2 = Asignacion.objects.filter(
        estacion__in=planta["estaciones"][:2]
    ).order_by("estacion__orden")
    capturar(jefe_en_captura, asignacion_1)

    # El jefe intercambia a los operadores de las estaciones 1 y 2.
    session = jefe_en_captura.session
    vigente = session[f"asignacion_vigente_{planta['linea'].id}"]
    e1, e2 = (str(e.id) for e in planta["estaciones"][:2])
    vigente[e1], vigente[e2] = vigente[e2], vigente[e1]
    session.save()
    jefe_en_captura.get(reverse("calidad:captura"))

    asignacion_1.refresh_from_db()
    asignacion_2.refresh_from_db()
    assert asignacion_1.empleado == planta["operadores"][0]  # ya tenía piezas: se conserva
    assert asignacion_2.empleado == planta["operadores"][0]  # sin piezas: se actualiza


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
    for selector in (".cap-horas a", ".cap-campo button", ".cap-campo input"):
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
    celdas = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", fila, re.S)]
    assert celdas == ["08:00", "Estación 3", "Operador 3", "117", "4", "3"]


# --- Turnos ------------------------------------------------------------------


def test_el_turno_3_cruza_la_medianoche():
    assert services.horas_del_turno(3) == [22, 23, 0, 1, 2, 3, 4, 5]
    assert services.turno_de_la_hora(2) == 3
    assert services.turno_de_la_hora(6) == 1
    assert services.turno_de_la_hora(21) == 2
