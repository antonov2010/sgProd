"""Pruebas unitarias y validación contra cálculo manual para KPIs (RF-3.2)."""

import pytest

from apps.dashboard.kpis import (
    calcular_fpy,
    calcular_piezas_hora_vs_meta,
    calcular_tasa_defectos,
    desglosar_kpis,
)


def test_fpy_coincide_con_calculo_manual():
    # Manual: 80 / (80 + 15 + 5) = 80 / 100 = 80.0 %
    assert calcular_fpy(80, 15, 5) == 80.0
    # Manual: 38 / (38 + 1 + 1) = 38 / 40 = 95.0 %
    assert calcular_fpy(38, 1, 1) == 95.0
    # Sin piezas debe devolver None sin error de división por cero
    assert calcular_fpy(0, 0, 0) is None


def test_tasa_defectos_coincide_con_calculo_manual():
    # Manual: 15 / (80 + 15 + 5) = 15.0 %
    assert calcular_tasa_defectos(80, 15, 5) == 15.0
    # Manual: 0 / 40 = 0.0 %
    assert calcular_tasa_defectos(40, 0, 0) == 0.0
    # Sin piezas
    assert calcular_tasa_defectos(0, 0, 0) is None


def test_piezas_hora_contra_meta_calculo_manual():
    # Manual: 90 aceptadas en 2 horas y 1 estación = 45.0 pzs/h vs meta 50.0 pzs/h (90.0 %)
    res = calcular_piezas_hora_vs_meta(aceptadas=90, meta=100, horas=2, estaciones=1)
    assert res == {
        "piezas_hora": 45.0,
        "meta_hora": 50.0,
        "diferencia": -5.0,
        "cumplimiento_pct": 90.0,
    }
    # Meta en 0 no rompe el cálculo
    sin_meta = calcular_piezas_hora_vs_meta(aceptadas=40, meta=0, horas=1, estaciones=1)
    assert sin_meta["cumplimiento_pct"] is None
    # Horas o estaciones en 0
    assert calcular_piezas_hora_vs_meta(aceptadas=40, meta=40, horas=0) is None


@pytest.fixture
def registros_conocidos():
    return [
        {
            "linea": "Línea 1",
            "estacion": "Corte",
            "turno": "Turno 1",
            "empleado": "Ana",
            "hora": "Hora 1",
            "aceptadas": 80,
            "rechazadas": 15,
            "retrabajo": 5,
            "meta": 100,
        },
        {
            "linea": "Línea 1",
            "estacion": "Soldadura",
            "turno": "Turno 2",
            "empleado": "Luis",
            "hora": "Hora 1",
            "aceptadas": 45,
            "rechazadas": 5,
            "retrabajo": 0,
            "meta": 50,
        },
    ]


def test_desglose_por_estacion_y_empleado(registros_conocidos):
    por_estacion = desglosar_kpis(registros_conocidos, "estacion")
    assert por_estacion["Corte"]["fpy"] == 80.0
    assert por_estacion["Corte"]["tasa_defectos"] == 15.0
    assert por_estacion["Soldadura"]["fpy"] == 90.0
    assert por_estacion["Soldadura"]["tasa_defectos"] == 10.0

    por_empleado = desglosar_kpis(registros_conocidos, "empleado")
    assert por_empleado["Ana"]["tasa_defectos"] == 15.0
    assert por_empleado["Luis"]["tasa_defectos"] == 10.0


def test_desglose_por_linea_y_turno(registros_conocidos):
    # Línea 1 total: 125 aceptadas, 20 rechazadas, 5 retrabajo = 150 total
    # Manual FPY: 125 / 150 = 83.3 % | Manual Defectos: 20 / 150 = 13.3 %
    por_linea = desglosar_kpis(registros_conocidos, "linea")
    assert por_linea["Línea 1"]["fpy"] == 83.3
    assert por_linea["Línea 1"]["tasa_defectos"] == 13.3
    assert por_linea["Línea 1"]["piezas_hora"]["cumplimiento_pct"] == 83.3

    por_turno = desglosar_kpis(registros_conocidos, "turno")
    assert por_turno["Turno 1"]["fpy"] == 80.0
    assert por_turno["Turno 2"]["fpy"] == 90.0


def test_dimension_invalida_lanza_error(registros_conocidos):
    with pytest.raises(ValueError):
        desglosar_kpis(registros_conocidos, "planta")