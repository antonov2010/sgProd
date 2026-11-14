import hashlib
from functools import wraps

from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.calidad import services as calidad_services
from apps.core.validacion import CuerpoInvalido, entero_positivo, objeto_json

from . import services
from .forms import LoginForm
from .models import Empleado, Estacion, SkillMatrix
from .services import generar_sugerencia_turno

# Bloqueo temporal del acceso por intentos fallidos (B-02). El contador vive
# en la cache local (locmem), por número de empleado + IP de origen.
MAX_INTENTOS_FALLIDOS = 5
VENTANA_INTENTOS_SEGUNDOS = 15 * 60
MENSAJE_BLOQUEO = (
    "Demasiados intentos fallidos. Espera 15 minutos e inténtalo de nuevo."
)


def jefe_de_linea_requerido(vista):
    """Solo un Jefe de Línea activo con sesión iniciada puede acceder."""

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
            if request.method == "POST" and "guardar_asignacion" not in request.POST:
                return JsonResponse(
                    {"success": False, "error": "Inicia sesión como Jefe de Línea."},
                    status=403,
                )
            messages.error(request, "Inicia sesión como Jefe de Línea para continuar.")
            return redirect("personal:login")

        request.jefe = jefe
        request.linea = calidad_services.linea_del_jefe(jefe)
        return vista(request, *args, **kwargs)

    return envoltura


def _turno_valido(valor, turno_actual):
    """Turno 1–3 enviado por la pantalla; si falta o no es válido, el actual."""
    try:
        turno = int(valor)
    except (TypeError, ValueError):
        return turno_actual
    return turno if turno in calidad_services.TURNOS else turno_actual


def _clave_intentos(num_emp, request):
    """Clave de cache que combina número de empleado e IP de origen."""
    ip = request.META.get("REMOTE_ADDR", "") or "sin-ip"
    semilla = f"{num_emp.casefold()}|{ip}"
    digest = hashlib.sha256(semilla.encode("utf-8")).hexdigest()
    return f"login_fallos:{digest}"


def _registrar_fallo(clave):
    """Suma un intento fallido y avisa si ya se alcanzó el bloqueo.

    Cada fallo reinicia la ventana de 15 minutos; al llegar al máximo la clave
    queda viva otros 15 minutos, que es lo que dura el bloqueo. El PIN recibido
    nunca se guarda: solo se cuenta el intento.
    """
    intentos = cache.get(clave, 0) + 1
    cache.set(clave, intentos, VENTANA_INTENTOS_SEGUNDOS)
    return intentos >= MAX_INTENTOS_FALLIDOS


def login_empleado(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            num_emp = form.cleaned_data["numero_empleado"].strip()
            pin_ingresado = form.cleaned_data["pin"].strip()
            clave_intentos = _clave_intentos(num_emp, request)

            if cache.get(clave_intentos, 0) >= MAX_INTENTOS_FALLIDOS:
                messages.error(request, MENSAJE_BLOQUEO)
            else:
                try:
                    empleado = Empleado.objects.get(numero_empleado__iexact=num_emp)
                except Empleado.DoesNotExist:
                    if _registrar_fallo(clave_intentos):
                        messages.error(request, MENSAJE_BLOQUEO)
                    else:
                        messages.error(
                            request,
                            "Acceso denegado: número de empleado no registrado.",
                        )
                else:
                    if not empleado.activo:
                        if _registrar_fallo(clave_intentos):
                            messages.error(request, MENSAJE_BLOQUEO)
                        else:
                            messages.error(
                                request,
                                "Acceso denegado: el usuario se encuentra inactivo.",
                            )
                    elif empleado.check_pin(pin_ingresado):
                        # Un acceso correcto limpia el contador de fallos.
                        cache.delete(clave_intentos)
                        request.session["empleado_id"] = empleado.id
                        request.session["empleado_nombre"] = empleado.nombre
                        request.session["numero_empleado"] = empleado.numero_empleado
                        tipo_rol = (
                            empleado.rol.tipo_rol.lower() if empleado.rol else "operador"
                        )
                        if "gerente" in tipo_rol:
                            return redirect("dashboard:pantalla_gerente")
                        if "jefe" in tipo_rol:
                            return redirect("dashboard:pantalla_jefe")
                        return redirect("dashboard:pantalla_operador")
                    else:
                        if _registrar_fallo(clave_intentos):
                            messages.error(request, MENSAJE_BLOQUEO)
                        else:
                            messages.error(request, "Acceso denegado: PIN incorrecto.")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


def logout_empleado(request):
    """Cierra la sesión de planta y regresa al acceso."""
    request.session.flush()
    return redirect("personal:login")


@jefe_de_linea_requerido
def matriz_competencias(request):
    linea_actual = request.linea
    if not linea_actual:
        return render(
            request,
            "matriz.html",
            {
                "linea": None,
                "turno": calidad_services.turno_de_la_hora(
                    calidad_services.hora_actual()
                ),
                "estaciones": [],
                "matriz": [],
                "mapa_niveles": {},
                "instructores_apoyo": {},
            },
        )

    estaciones = Estacion.objects.filter(linea=linea_actual).order_by("orden")
    empleados = Empleado.objects.filter(
        linea=linea_actual, activo=True, rol__tipo_rol__iexact="operador"
    ).order_by("nombre")

    # El turno que se está viendo viaja en el formulario (hidden) y en la URL.
    # Se calcula una sola vez: la tabla y el guardado usan el mismo turno.
    turno_actual = calidad_services.turno_de_la_hora(calidad_services.hora_actual())
    turno = _turno_valido(
        request.POST.get("turno") if request.method == "POST" else request.GET.get("turno"),
        turno_actual,
    )
    # La fecha sale del turno que se está viendo, no del reloj: de madrugada el
    # turno 3 sigue siendo la guardia que arrancó ayer a las 22:00 (B-05).
    fecha = calidad_services.fecha_de_la_guardia(turno)

    # 1. Procesar guardado de asignación (POST) validando pertenencia a la línea
    if request.method == "POST" and "guardar_asignacion" in request.POST:
        estaciones_validas = {str(e.id) for e in estaciones}
        empleados_validos = {str(emp.id) for emp in empleados}
        asignaciones_guardadas = {}

        for key, val in request.POST.items():
            if key.startswith("estacion_"):
                estacion_id = key.replace("estacion_", "")
                if estacion_id in estaciones_validas:
                    asignaciones_guardadas[estacion_id] = (
                        val if (val and val in empleados_validos) else None
                    )

        _, guardadas, _, avisos = calidad_services.guardar_asignacion_vigente(
            linea_actual, asignaciones_guardadas, fecha=fecha, turno=turno
        )
        asignadas = sum(1 for asignacion in guardadas.values() if asignacion)
        messages.success(
            request,
            f"Asignación vigente guardada para el turno {turno}: {asignadas} de "
            f"{len(guardadas)} estaciones.",
        )
        for aviso in avisos:
            messages.warning(request, aviso)
        return redirect(f"{reverse('personal:matriz_competencias')}?turno={turno}")

    # 2. Consultar habilidades de la línea
    habilidades = SkillMatrix.objects.filter(
        empleado__in=empleados, estacion__in=estaciones
    )
    mapa_habilidades = {(h.empleado_id, h.estacion_id): h.nivel for h in habilidades}

    # 3. Construir Matriz General
    matriz = []
    for emp in empleados:
        fila_niveles = []
        for est in estaciones:
            nivel = mapa_habilidades.get((emp.id, est.id), None)
            fila_niveles.append({"estacion_id": est.id, "nivel": nivel})
        matriz.append({"empleado": emp, "niveles": fila_niveles})

    # 4. Construir Mapa de Instructores por Estación (para US-09)
    instructores_por_estacion = {}
    for est in estaciones:
        instructores = [
            h.empleado
            for h in habilidades
            if h.estacion_id == est.id and h.nivel == "Instructor"
        ]
        instructores_por_estacion[est.id] = instructores

    # 5. CONSTRUIR TABLA 1: ASIGNACIÓN VIGENTE DE LA LÍNEA
    # Se lee de la base (US-08) con el mismo turno que se está viendo, no con
    # el reloj: la sesión del navegador ya no es la fuente de verdad.
    _, asignaciones_vigentes, _ = calidad_services.asignaciones_del_turno(
        linea_actual, turno, fecha
    )
    tabla_vigente_estatica = []

    for est in estaciones:
        asignacion = asignaciones_vigentes.get(est.id)
        emp_obj = asignacion.empleado if asignacion else None

        nivel = mapa_habilidades.get((emp_obj.id, est.id)) if emp_obj else None
        # Una estación descubierta no es una alerta de nivel: sin operador no
        # corresponde mostrar «Sin Nivel Asignado» ni sugerir Instructor.
        es_principiante = bool(emp_obj) and (nivel == "Principiante" or not nivel)

        instructores = instructores_por_estacion.get(est.id, [])
        instructor_apoyo = (
            instructores[0] if (es_principiante and instructores) else None
        )

        tabla_vigente_estatica.append(
            {
                "estacion": est,
                "empleado_asignado": emp_obj,
                "nivel": nivel,
                "es_principiante": es_principiante,
                "instructor_apoyo": instructor_apoyo,
            }
        )

    # 6. CONSTRUIR TABLA 2: SUGERENCIA DE DISTRIBUCIÓN
    sugerencia_propuesta = None
    if request.GET.get("sugerir") == "1":
        sugerencia_propuesta = generar_sugerencia_turno(linea_actual)

        for item in sugerencia_propuesta["asignaciones"]:
            emp = item.get("empleado")
            est = item["estacion"]

            nivel = mapa_habilidades.get((emp.id, est.id)) if emp else None
            item["nivel"] = nivel
            item["es_principiante"] = bool(emp) and (
                nivel == "Principiante" or not nivel
            )

            instructores = instructores_por_estacion.get(est.id, [])
            item["instructor_apoyo"] = (
                instructores[0] if (item["es_principiante"] and instructores) else None
            )

    # El template recibe diccionarios (no JSON en texto) y los publica con
    # ``json_script``: evita inyectar datos sin escapar dentro de <script>.
    mapa_niveles = {
        f"{h.empleado_id}_{h.estacion_id}": h.nivel for h in habilidades
    }
    # US-09: al cambiar la asignación a mano, el template necesita saber quién
    # puede apoyar como Instructor en cada estación.
    instructores_apoyo = {
        str(estacion_id): instructores[0].nombre
        for estacion_id, instructores in instructores_por_estacion.items()
        if instructores
    }

    return render(
        request,
        "matriz.html",
        {
            "linea": linea_actual,
            "turno": turno,
            "estaciones": estaciones,
            "matriz": matriz,
            "tabla_vigente_estatica": tabla_vigente_estatica,
            "sugerencia_propuesta": sugerencia_propuesta,
            "todos_los_operadores": empleados,
            "mapa_niveles": mapa_niveles,
            "instructores_apoyo": instructores_apoyo,
        },
    )


@require_POST
@jefe_de_linea_requerido
def actualizar_nivel_matriz(request):
    if request.linea is None:
        return JsonResponse(
            {"success": False, "error": "No tienes una línea asignada."}, status=403
        )

    try:
        data = objeto_json(request.body)
    except CuerpoInvalido as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)

    try:
        empleado_id = entero_positivo(data.get("empleado_id"), "empleado_id")
        estacion_id = entero_positivo(data.get("estacion_id"), "estacion_id")
        nivel = data.get("nivel")
        if not isinstance(nivel, str) or not nivel.strip():
            raise CuerpoInvalido("Falta el campo obligatorio «nivel».")
    except CuerpoInvalido as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)

    empleado = Empleado.objects.filter(pk=empleado_id, linea=request.linea).first()
    if empleado is None:
        return JsonResponse(
            {"success": False, "error": "El empleado no pertenece a tu línea."},
            status=403,
        )

    estacion = Estacion.objects.filter(pk=estacion_id, linea=request.linea).first()
    if estacion is None:
        return JsonResponse(
            {"success": False, "error": "La estación no pertenece a tu línea."},
            status=403,
        )

    try:
        nivel = services.actualizar_nivel(
            empleado.id, estacion.id, nivel, linea=request.linea
        )
    except services.NivelInvalido as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": True, "nivel": nivel})
