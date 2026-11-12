from django.shortcuts import render

from .datos_ejemplo import personal_ejemplo, registros_ejemplo
from .datos_reales import personal_real, registros_reales
from .tablero import construir_tablero


def pantalla_operador(request):
    return render(request, 'dashboard/operador.html')


def pantalla_jefe(request):
    return render(request, 'dashboard/jefe.html')


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
    tablero = construir_tablero(registros, personal)
    return render(
        request,
        'dashboard/gerente.html',
        {'tablero': tablero, 'tablero_es_ejemplo': es_ejemplo},
    )
