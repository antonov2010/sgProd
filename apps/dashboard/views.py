from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.personal.models import Empleado

from .accesos import rol_requerido
from .bonos import calcular_elegibles_bono
from .config_umbrales import umbrales_actuales
from .datos_ejemplo import personal_ejemplo, registros_ejemplo
from .datos_reales import personal_real, registros_reales
from .tablero import construir_tablero


@rol_requerido('operador')
def pantalla_operador(request):
    return render(request, 'dashboard/operador.html')


@rol_requerido('jefe')
def pantalla_jefe(request):
    return render(request, 'dashboard/jefe.html')


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
    return render(
        request,
        'dashboard/gerente.html',
        {
            'tablero': tablero,
            'tablero_es_ejemplo': es_ejemplo,
            'bono': bono,
        },
    )


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