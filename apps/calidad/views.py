"""Pantallas de calidad: captura horaria por estación (US-11, RF-2.1, RF-2.2)."""

import json
import time
from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.personal.models import Empleado

from . import services
from .models import CatalogoDefecto


def jefe_de_linea_requerido(vista):
    """Solo el Jefe de Línea con sesión de planta activa entra a la captura."""

    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        jefe = (
            Empleado.objects.filter(
                pk=request.session.get("empleado_id"),
                activo=True,
                rol__tipo_rol__iexact="jefe",
            )
            .select_related("linea")
            .first()
        )
        if jefe is None:
            if request.method == "POST":
                return JsonResponse(
                    {"ok": False, "error": "Inicia sesión como Jefe de Línea."}, status=403
                )
            messages.error(request, "Inicia sesión como Jefe de Línea para capturar.")
            return redirect("personal:login")
        request.jefe = jefe
        request.linea = services.linea_del_jefe(jefe)
        return vista(request, *args, **kwargs)

    return envoltura


@jefe_de_linea_requerido
def captura_horaria(request):
    linea = request.linea
    if linea is None:
        return render(request, "calidad/captura.html", {"linea": None})

    turno = services.turno_de_la_hora(services.hora_actual())
    horas = services.horas_del_turno(turno)
    try:
        hora = int(request.GET.get("hora", services.hora_actual()))
    except ValueError:
        hora = services.hora_actual()
    if hora not in horas:
        hora = services.hora_actual()

    vigente = request.session.get(f"asignacion_vigente_{linea.id}", {})
    filas = services.estaciones_para_capturar(linea, turno, hora, vigente)

    return render(
        request,
        "calidad/captura.html",
        {
            "linea": linea,
            "turno": turno,
            "horas": horas,
            "hora": hora,
            "filas": filas,
            "sin_asignar": sum(1 for f in filas if f.asignacion is None),
            "historial": services.historial_del_turno(linea, turno),
            "catalogo_defectos": CatalogoDefecto.objects.order_by("codigo"),
        },
    )


@require_POST
@jefe_de_linea_requerido
def guardar_captura(request):
    """Guarda una estación. Responde en JSON para no recargar la pantalla (RNF-2)."""
    inicio = time.perf_counter()
    try:
        datos = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Cuerpo JSON inválido."}, status=400)
    if request.linea is None:
        return JsonResponse({"ok": False, "error": "No tienes una línea asignada."}, status=400)

    try:
        registro, creado = services.registrar_captura(
            request.linea,
            datos.get("asignacion_id"),
            datos.get("hora"),
            datos.get("aceptadas"),
            datos.get("rechazadas"),
            datos.get("retrabajo"),
            defecto_id=datos.get("defecto_id"),
        )
    except services.CapturaInvalida as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    primer_defecto = registro.defectos.select_related("defecto").first()

    return JsonResponse(
        {
            "ok": True,
            "creado": creado,
            "registro": {
                "id": registro.id,
                "hora": registro.hora,
                "estacion": registro.asignacion.estacion.nombre,
                "operador": registro.asignacion.empleado.nombre,
                "aceptadas": registro.piezas_aceptadas,
                "rechazadas": registro.piezas_rechazadas,
                "retrabajo": registro.piezas_retrabajo,
                "defecto": str(primer_defecto.defecto) if primer_defecto else "—",
            },
            "ms": round((time.perf_counter() - inicio) * 1000),
        },
        status=201 if creado else 200,
    )