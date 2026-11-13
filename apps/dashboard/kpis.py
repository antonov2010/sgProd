"""Fórmulas y desgloses de KPIs de producción y calidad (RF-3.2)."""


def calcular_fpy(aceptadas, rechazadas, retrabajo):
    """First Pass Yield: aceptadas / (aceptadas + rechazadas + retrabajo) en %."""
    total = aceptadas + rechazadas + retrabajo
    if total == 0:
        return None
    return round(100 * aceptadas / total, 1)


def calcular_tasa_defectos(aceptadas, rechazadas, retrabajo):
    """Porcentaje de piezas defectuosas respecto al total producido."""
    total = aceptadas + rechazadas + retrabajo
    if total == 0:
        return None
    return round(100 * rechazadas / total, 1)


def calcular_piezas_hora_vs_meta(aceptadas, meta, horas=1, estaciones=1):
    """Compara piezas aceptadas por hora contra la meta configurada."""
    base = horas * estaciones
    if base <= 0:
        return None
    piezas_hora = round(aceptadas / base, 1)
    meta_hora = round(meta / base, 1)
    cumplimiento = round(100 * aceptadas / meta, 1) if meta > 0 else None
    return {
        "piezas_hora": piezas_hora,
        "meta_hora": meta_hora,
        "diferencia": round(piezas_hora - meta_hora, 1),
        "cumplimiento_pct": cumplimiento,
    }


def _acumular(registros):
    """Suma totales de piezas, metas y combinaciones únicas de hora/estación."""
    totales = {"aceptadas": 0, "rechazadas": 0, "retrabajo": 0, "meta": 0}
    horas = set()
    estaciones = set()
    for r in registros:
        totales["aceptadas"] += r["aceptadas"]
        totales["rechazadas"] += r["rechazadas"]
        totales["retrabajo"] += r["retrabajo"]
        totales["meta"] += r["meta"]
        if "hora" in r:
            horas.add(r["hora"])
        if "estacion" in r:
            estaciones.add(r["estacion"])
    return totales, max(len(horas), 1), max(len(estaciones), 1)


def desglosar_kpis(registros, dimension):
    """Calcula FPY, Piezas/Hora vs Meta y Tasa de Defectos por estación, línea, turno o empleado."""
    dimensiones_validas = {"estacion", "linea", "turno", "empleado"}
    if dimension not in dimensiones_validas:
        raise ValueError(f"Dimensión no soportada: {dimension}")

    grupos = {}
    for r in registros:
        clave = r.get(dimension)
        if clave is not None:
            grupos.setdefault(clave, []).append(r)

    resultado = {}
    for clave, regs in grupos.items():
        totales, num_horas, num_estaciones = _acumular(regs)
        resultado[clave] = {
            "fpy": calcular_fpy(
                totales["aceptadas"], totales["rechazadas"], totales["retrabajo"]
            ),
            "tasa_defectos": calcular_tasa_defectos(
                totales["aceptadas"], totales["rechazadas"], totales["retrabajo"]
            ),
            "piezas_hora": calcular_piezas_hora_vs_meta(
                totales["aceptadas"],
                totales["meta"],
                horas=num_horas,
                estaciones=num_estaciones,
            ),
        }
    return resultado