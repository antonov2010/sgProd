"""Reglas de negocio de la matriz de habilidades (RF-1.2 y RF-1.4).

La lógica vive aquí y no en las vistas para que la pantalla HTML
(``personal:actualizar_nivel_matriz``) y el endpoint REST
(``api:matriz-nivel``) apliquen exactamente las mismas validaciones.
"""

from .models import Empleado, Estacion, NivelHabilidad, SkillMatrix

NIVEL_SIN_ASIGNAR = "Sin nivel"
NIVELES_PERMITIDOS = [*NivelHabilidad.values, NIVEL_SIN_ASIGNAR]


class NivelInvalido(ValueError):
    """El nivel recibido no es uno de los cuatro niveles del catálogo."""


def actualizar_nivel(empleado_id, estacion_id, nivel, linea=None):
    """Actualiza o elimina el nivel de habilidad de un empleado en una estación."""
    if not empleado_id or not estacion_id:
        raise NivelInvalido("Faltan identificadores de empleado o estación.")

    empleado = Empleado.objects.get(pk=empleado_id)
    estacion = Estacion.objects.get(pk=estacion_id)

    if linea is not None:
        if empleado.linea_id != linea.id:
            raise NivelInvalido("El empleado no pertenece a la línea autorizada.")
        if estacion.linea_id != linea.id:
            raise NivelInvalido("La estación no pertenece a la línea autorizada.")

    if not nivel:
        SkillMatrix.objects.filter(empleado=empleado, estacion=estacion).delete()
        return None

    niveles_validos = {choice[0] for choice in NivelHabilidad.choices}
    if nivel not in niveles_validos:
        raise NivelInvalido(f"Nivel no válido: {nivel}")

    obj, _ = SkillMatrix.objects.update_or_create(
        empleado=empleado,
        estacion=estacion,
        defaults={"nivel": nivel},
    )
    return obj.nivel


# ------------------------------------------------------------------
# RF-1.4: Puntos de extensión para Asistencia / Checador (Karen)
# ------------------------------------------------------------------

def obtener_personal_presente(linea):
    """
    HOOK DE ASISTENCIA (RF-1.4):
    Punto de extensión aislado para integración futura con reloj checador/biométrico/RFID.
    
    Comportamiento actual:
    - Asume por defecto a todo el personal activo de la línea.
    - Excluye automáticamente a los empleados dados de baja (activo=False).
    """
    return list(
        Empleado.objects.filter(
            linea=linea, 
            activo=True, 
            rol__tipo_rol__iexact='operador'
        )
    )


# Peso numérico por nivel para ordenar a los candidatos (RF-1.3)
PESOS_NIVEL = {
    'Instructor': 4,
    'Experto': 3,
    'Autónomo': 2,
    'Principiante': 1,
}

def generar_sugerencia_turno(linea):
    """
    Genera una distribución de personal para todas las estaciones de la línea.
    Criterios de Aceptación RF-1.3 & RF-1.4:
    1. Consume el hook de asistencia para tomar por defecto a todo el personal activo.
    2. Propone una distribución completa (una persona por estación).
    3. Si no hay personal con nivel suficiente, la marca como 'descubierta'.
    """
    estaciones = Estacion.objects.filter(linea=linea).order_by('orden')
    
    # RF-1.4: Asume por defecto el personal activo retornando del Hook de Asistencia
    operadores_disponibles = obtener_personal_presente(linea)
    
    # Obtener todas las calificaciones registradas en la línea
    habilidades = SkillMatrix.objects.filter(
        empleado__in=operadores_disponibles, 
        estacion__in=estaciones
    )
    
    # Mapa (empleado_id, estacion_id) -> peso
    mapa_pesos = {}
    for h in habilidades:
        peso = PESOS_NIVEL.get(h.nivel, 0)
        mapa_pesos[(h.empleado_id, h.estacion_id)] = peso

    asignaciones = []
    operadores_asignados = set()

    # Iterar estación por estación para buscar el mejor candidato disponible
    for estacion in estaciones:
        candidatos = []
        for emp in operadores_disponibles:
            if emp.id in operadores_asignados:
                continue
            
            peso = mapa_pesos.get((emp.id, estacion.id), 0)
            # Solo consideramos aptos a quienes tienen nivel (peso > 0)
            if peso > 0:
                candidatos.append((peso, emp))
        
        # Ordenar candidatos por el de mayor nivel
        candidatos.sort(key=lambda x: x[0], reverse=True)

        if candidatos:
            _, mejor_empleado = candidatos[0]
            operadores_asignados.add(mejor_empleado.id)
            asignaciones.append({
                'estacion': estacion,
                'empleado': mejor_empleado,
                'descubierta': False,
            })
        else:
            # Criterio 2: Si no hay personal apto/disponible, marcar como descubierta
            asignaciones.append({
                'estacion': estacion,
                'empleado': None,
                'descubierta': True,
            })

    # Operadores que quedaron libres para cambios manuales
    sin_asignar = [emp for emp in operadores_disponibles if emp.id not in operadores_asignados]

    return {
        'linea': linea,
        'asignaciones': asignaciones,
        'sin_asignar': sin_asignar,
    }