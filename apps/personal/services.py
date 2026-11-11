"""Reglas de negocio de la matriz de habilidades (RF-1.2).

La lógica vive aquí y no en las vistas para que la pantalla HTML
(``personal:actualizar_nivel_matriz``) y el endpoint REST
(``api:matriz-nivel``) apliquen exactamente las mismas validaciones.
"""

from .models import Empleado, Estacion, NivelHabilidad, SkillMatrix

NIVEL_SIN_ASIGNAR = "Sin nivel"
NIVELES_PERMITIDOS = [*NivelHabilidad.values, NIVEL_SIN_ASIGNAR]


class NivelInvalido(ValueError):
    """El nivel recibido no es uno de los cuatro niveles del catálogo."""


def actualizar_nivel(empleado_id, estacion_id, nivel):
    """Crea, actualiza o elimina el nivel de un empleado en una estación.

    Devuelve el nivel efectivamente guardado. Lanza ``NivelInvalido`` si el
    nivel no pertenece al catálogo, y ``Empleado.DoesNotExist`` /
    ``Estacion.DoesNotExist`` si las llaves foráneas no existen.

    ``Sin nivel`` borra el registro: la matriz se representa con ausencia de
    fila en lugar de con un valor de relleno.
    """
    if nivel not in NIVELES_PERMITIDOS:
        raise NivelInvalido(
            f"Nivel no válido. Debe ser uno de: {', '.join(NIVELES_PERMITIDOS)}"
        )

    empleado = Empleado.objects.get(pk=empleado_id)
    estacion = Estacion.objects.get(pk=estacion_id)

    if nivel == NIVEL_SIN_ASIGNAR:
        SkillMatrix.objects.filter(empleado=empleado, estacion=estacion).delete()
        return NIVEL_SIN_ASIGNAR

    SkillMatrix.objects.update_or_create(
        empleado=empleado,
        estacion=estacion,
        defaults={"nivel": nivel},
    )
    return nivel

from .models import Empleado, Estacion, SkillMatrix

# Peso numérico por nivel para ordenar a los candidatos
PESOS_NIVEL = {
    'Instructor': 4,
    'Experto': 3,
    'Autónomo': 2,
    'Principiante': 1,
}

def generar_sugerencia_turno(linea):
    """
    Genera una distribución de personal para todas las estaciones de la línea.
    Criterios de Aceptación RF-1.3:
    1. Propone una distribución completa (una persona por estación).
    2. Si no hay personal con nivel suficiente, la marca como 'descubierta'.
    """
    estaciones = Estacion.objects.filter(linea=linea).order_by('orden')
    operadores_disponibles = list(
        Empleado.objects.filter(linea=linea, activo=True, rol__tipo_rol__iexact='operador')
    )
    
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