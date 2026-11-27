from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.calidad import services as calidad_services
from apps.calidad.models import Asignacion, RegistroCalidadHorario
from apps.personal.models import Empleado, SkillMatrix

from .accesos import rol_requerido
from .bonos import calcular_elegibles_bono
from .config_umbrales import umbrales_actuales
from .datos_ejemplo import personal_ejemplo, registros_ejemplo
from .datos_reales import personal_real, registros_reales
from .jefe_kpis import construir_indicadores_jefe
from .tablero import construir_tablero


@rol_requerido('operador')
def pantalla_operador(request):
    empleado = request.empleado
    hora = calidad_services.hora_actual()
    turno_actual = calidad_services.turno_de_la_hora(hora)
    fecha_actual = calidad_services.fecha_de_la_guardia(turno_actual)

    # 1. Buscar asignación del turno en curso; si no hay (ej. demo fuera de turno 1),
    # toma la asignación más reciente del operador para mostrar datos reales.
    asignacion = (
        Asignacion.objects.filter(
            empleado=empleado,
            fecha=fecha_actual,
            turno=turno_actual,
        )
        .select_related('estacion', 'estacion__linea')
        .first()
    )
    es_turno_vigente = asignacion is not None
    if asignacion is None:
        asignacion = (
            Asignacion.objects.filter(empleado=empleado)
            .select_related('estacion', 'estacion__linea')
            .order_by('-fecha', '-turno', '-id')
            .first()
        )

    nivel_habilidad = None
    if asignacion is not None:
        skill = SkillMatrix.objects.filter(
            empleado=empleado,
            estacion=asignacion.estacion,
        ).first()
        nivel_habilidad = skill.nivel if skill else 'Sin nivel'

    # 2. Producción y calidad de esa asignación
    produccion = {
        'aceptadas': 0,
        'rechazadas': 0,
        'retrabajo': 0,
        'total': 0,
        'fpy': None,
        'horas_registradas': 0,
    }
    if asignacion is not None:
        registros = RegistroCalidadHorario.objects.filter(asignacion=asignacion)
        agregados = registros.aggregate(
            aceptadas=Sum('piezas_aceptadas'),
            rechazadas=Sum('piezas_rechazadas'),
            retrabajo=Sum('piezas_retrabajo'),
        )
        aceptadas = agregados['aceptadas'] or 0
        rechazadas = agregados['rechazadas'] or 0
        retrabajo = agregados['retrabajo'] or 0
        total = aceptadas + rechazadas + retrabajo
        fpy = round((aceptadas / total) * 100, 1) if total > 0 else None
        produccion = {
            'aceptadas': aceptadas,
            'rechazadas': rechazadas,
            'retrabajo': retrabajo,
            'total': total,
            'fpy': fpy,
            'horas_registradas': registros.count(),
        }

    # 3. Elegibilidad al bono por cero defectos (US-15)
    bono = calcular_elegibles_bono()
    detalle_bono = next(
        (item for item in bono['elegibles'] if item['empleado_id'] == empleado.id),
        None,
    )
    agregados_periodo = RegistroCalidadHorario.objects.filter(
        asignacion__empleado=empleado,
        asignacion__fecha__range=(bono['periodo']['inicio'], bono['periodo']['fin']),
    ).aggregate(
        total_aceptadas=Sum('piezas_aceptadas'),
        total_rechazos=Sum('piezas_rechazadas'),
    )
    aceptadas_periodo = agregados_periodo['total_aceptadas'] or 0
    rechazos_periodo = agregados_periodo['total_rechazos'] or 0

    return render(
        request,
        'dashboard/operador.html',
        {
            'empleado': empleado,
            'asignacion': asignacion,
            'es_turno_vigente': es_turno_vigente,
            'nivel_habilidad': nivel_habilidad,
            'produccion': produccion,
            'bono': bono,
            'detalle_bono': detalle_bono,
            'aceptadas_periodo': aceptadas_periodo,
            'rechazos_periodo': rechazos_periodo,
        },
    )


@rol_requerido('jefe')
def pantalla_jefe(request):
    # El turno se resuelve con el mismo reloj que la captura: de madrugada, el
    # turno 3 sigue perteneciendo a la guardia que inició la noche anterior.
    hora = calidad_services.hora_actual()
    turno = calidad_services.turno_de_la_hora(hora)
    fecha = calidad_services.fecha_de_la_guardia(turno)
    linea = calidad_services.linea_del_jefe(request.empleado)
    return render(
        request,
        'dashboard/jefe.html',
        {
            'linea': linea,
            'turno': turno,
            'hora': hora,
            'indicadores': construir_indicadores_jefe(linea, turno, hora, fecha),
        },
    )


@rol_requerido('gerente')
def pantalla_gerente(request):
    # US-13: usa los registros reales de calidad. Si todavía no hay captura
    # horaria en la base, muestra datos de EJEMPLO con un aviso visible.
    registros = registros_reales()
    es_ejemplo = not registros
    if es_ejemplo:
        registros = registros_ejemplo()
        personal = personal_ejemplo()
    else:
        personal = personal_real()
    tablero = construir_tablero(registros, personal, umbrales_actuales())
    bono = calcular_elegibles_bono()
    # RNF-4: la lista de elegibles se pagina de 10 en 10 para no volcar todo
    # el padrón de golpe en pantallas de gerencia.
    pagina_elegibles = Paginator(bono['elegibles'], 10).get_page(
        request.GET.get('pagina')
    )
    # Rango visible de la página («Mostrando 1–10 de 31»). get_page() devuelve
    # 0–0 cuando no hay elegibles, sin levantar EmptyPage.
    rango_pagina = {
        'desde': pagina_elegibles.start_index(),
        'hasta': pagina_elegibles.end_index(),
        'total': pagina_elegibles.paginator.count,
    }
    contexto = {
        'tablero': tablero,
        'tablero_es_ejemplo': es_ejemplo,
        'bono': bono,
        'pagina_elegibles': pagina_elegibles,
        'rango_pagina': rango_pagina,
    }
    # La paginación de bonos se resuelve por fetch y solo reemplaza la tabla.
    # Sin JavaScript se sigue sirviendo la pantalla completa con ?pagina=N.
    if request.GET.get('fragmento') == 'bonos':
        return render(request, 'dashboard/_bonos_tabla.html', contexto)
    return render(request, 'dashboard/gerente.html', contexto)


@rol_requerido('gerente')
def detalle_elegible_bono(request, empleado_id):
    """Muestra los registros horarios que sustentan la elegibilidad de un operador (US-15)."""
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    bono = calcular_elegibles_bono()
    detalle = next(
        (item for item in bono['elegibles'] if item['empleado_id'] == empleado.id),
        None,
    )
    if detalle is None:
        raise Http404("El operador no es elegible a bono en el periodo evaluado.")
    return render(
        request,
        'dashboard/bono_detalle.html',
        {
            'empleado': empleado,
            'detalle': detalle,
            'periodo': bono['periodo'],
        },
    )