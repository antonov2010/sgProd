"""Indicadores reales del turno en curso para el tablero del jefe de línea.

Solo lee: las asignaciones y los registros horarios ya capturados se consultan
a través de ``apps.calidad.services`` y la fórmula de FPY vive en
``apps.dashboard.kpis``. Así la pantalla no duplica reglas de negocio.
"""

from apps.calidad import services as calidad

from .kpis import calcular_fpy


def construir_indicadores_jefe(linea, turno, hora, fecha):
    """Arma los tres KPIs del turno del jefe.

    ``linea`` puede ser ``None`` (jefe sin línea asignada): la pantalla debe
    seguir respondiendo con indicadores vacíos en lugar de romperse.
    """
    if linea is None:
        return [
            {
                "clave": "fpy",
                "nombre": "FPY del turno",
                "valor": "—",
                "unidad": "",
                "contexto": "Sin datos del turno",
            },
            {
                "clave": "cobertura",
                "nombre": "Cobertura de estaciones",
                "valor": "0",
                "unidad": "de 0",
                "contexto": "Sin estaciones en la línea",
            },
            {
                "clave": "capturas",
                "nombre": "Capturas de la hora",
                "valor": "0",
                "unidad": "de 0",
                "contexto": f"estaciones capturadas a las {hora:02d}:00",
            },
        ]

    # Una sola lectura de las estaciones del turno: de ahí salen la cobertura
    # (asignaciones con empleado activo) y las capturas de la hora actual.
    filas = calidad.estaciones_para_capturar(linea, turno, hora, fecha)
    total = len(filas)
    asignadas = sum(1 for fila in filas if fila.asignacion is not None)
    capturadas = sum(1 for fila in filas if fila.registro is not None)

    # FPY del turno completo, no solo de la hora visible en la captura.
    registros = calidad.historial_del_turno(linea, turno, fecha)
    aceptadas = sum(r.piezas_aceptadas for r in registros)
    rechazadas = sum(r.piezas_rechazadas for r in registros)
    retrabajo = sum(r.piezas_retrabajo for r in registros)
    fpy = calcular_fpy(aceptadas, rechazadas, retrabajo)

    if fpy is None:
        kpi_fpy = {
            "clave": "fpy",
            "nombre": "FPY del turno",
            "valor": "—",
            "unidad": "",
            "contexto": "Sin datos de captura del turno",
        }
    else:
        kpi_fpy = {
            "clave": "fpy",
            "nombre": "FPY del turno",
            "valor": f"{fpy:.1f}",
            "unidad": "%",
            "contexto": f"Turno {turno} · {fecha:%d/%m/%Y}",
        }

    return [
        kpi_fpy,
        {
            "clave": "cobertura",
            "nombre": "Cobertura de estaciones",
            "valor": str(asignadas),
            "unidad": f"de {total}",
            "contexto": (
                "estaciones con operador activo"
                if total
                else "Sin estaciones en la línea"
            ),
        },
        {
            "clave": "capturas",
            "nombre": "Capturas de la hora",
            "valor": str(capturadas),
            "unidad": f"de {total}",
            "contexto": f"estaciones capturadas a las {hora:02d}:00",
        },
    ]
