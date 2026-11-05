from django.shortcuts import render

from .datos_ejemplo import personal_ejemplo, registros_ejemplo
from .tablero import construir_tablero


def pantalla_operador(request):
    return render(request, 'dashboard/operador.html')


def pantalla_jefe(request):
    return render(request, 'dashboard/jefe.html')


def pantalla_gerente(request):
    # PROVISIONAL (US-13): datos de ejemplo. Cuando existan los registros
    # reales, solo se cambian registros_ejemplo() y personal_ejemplo() por
    # las consultas reales; construir_tablero() y la plantilla siguen igual.
    tablero = construir_tablero(registros_ejemplo(), personal_ejemplo())
    return render(request, 'dashboard/gerente.html', {'tablero': tablero})
