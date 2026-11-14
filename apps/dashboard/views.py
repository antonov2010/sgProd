from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.calidad import services as calidad_services
from apps.personal.models import Empleado

from .accesos import rol_requerido
from .bonos import calcular_elegibles_bono
from .config_umbrales import umbrales_actuales
from .datos_ejemplo import personal_ejemplo, registros_ejemplo
from .datos_reales import personal_real, registros_reales
from .jefe_kpis import construir_indicadores_jefe
from .tablero import construir_tablero


@rol_requerido('operador')
def pantalla_operador(request):
    return render(request, 'dashboard/operador.html')


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