"""Pruebas del cálculo del tablero (las fórmulas de KPI exigen 100 %)."""

from .datos_ejemplo import registros_ejemplo
from .tablero import construir_tablero, cumplimiento_meta, fpy, tasa_defectos
from .umbrales import UMBRALES, peor, semaforo


def test_fpy_coincide_con_el_calculo_manual():
    assert fpy(90, 5, 5) == 90.0


def test_fpy_sin_piezas_es_none():
    assert fpy(0, 0, 0) is None


def test_tasa_de_defectos():
    assert tasa_defectos(90, 5, 5) == 5.0
    assert tasa_defectos(0, 0, 0) is None


def test_cumplimiento_de_meta():
    assert cumplimiento_meta(80, 100) == 80.0
    assert cumplimiento_meta(10, 0) is None


def test_semaforo_indicador_donde_mayor_es_mejor():
    assert semaforo(96, "fpy") == "ok"
    assert semaforo(95, "fpy") == "ok"
    assert semaforo(92, "fpy") == "warn"
    assert semaforo(90, "fpy") == "warn"
    assert semaforo(89.9, "fpy") == "bad"


def test_semaforo_indicador_donde_menor_es_mejor():
    assert semaforo(1, "defectos") == "ok"
    assert semaforo(2, "defectos") == "ok"
    assert semaforo(4, "defectos") == "warn"
    assert semaforo(5, "defectos") == "warn"
    assert semaforo(6, "defectos") == "bad"


def test_semaforo_sin_datos():
    assert semaforo(None, "fpy") == "none"


def test_peor_estado():
    assert peor(["ok", "warn", "bad"]) == "bad"
    assert peor(["ok", "warn"]) == "warn"
    assert peor([]) == "none"


def test_el_tablero_cambia_de_color_al_cambiar_el_umbral_sin_tocar_codigo():
    registros = registros_ejemplo()
    normal = construir_tablero(registros)
    estricto = {
        **UMBRALES,
        "fpy": {"verde": 99.9, "amarillo": 99.0, "mejor": "alto"},
    }
    cambiado = construir_tablero(registros, estricto)
    assert normal["kpis"][0]["estado"] != cambiado["kpis"][0]["estado"]


def test_la_estacion_que_cae_pone_en_rojo_o_amarillo_su_linea():
    tablero = construir_tablero(registros_ejemplo())
    linea3 = next(x for x in tablero["lineas"] if x["nombre"] == "Línea 3")
    assert linea3["estado"] in ("warn", "bad")


def test_la_tendencia_tiene_un_punto_por_hora():
    tablero = construir_tablero(registros_ejemplo())
    assert len(tablero["tendencia"]["puntos"]) == 8


def test_la_grafica_grande_muestra_la_linea_con_peor_estado():
    tablero = construir_tablero(registros_ejemplo())
    assert tablero["tendencia"]["titulo"] == "Línea 3"


def test_sin_registros_no_truena():
    tablero = construir_tablero([])
    assert tablero["lineas"] == []
    assert tablero["tendencia"] is None
    assert tablero["kpis"][0]["estado"] == "none"
