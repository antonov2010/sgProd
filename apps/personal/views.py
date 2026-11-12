import json
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import LoginForm
from .models import Empleado, Estacion, Linea, SkillMatrix
from .services import generar_sugerencia_turno


def login_empleado(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            num_emp = form.cleaned_data["numero_empleado"].strip()
            pin_ingresado = form.cleaned_data["pin"].strip()

            try:
                empleado = Empleado.objects.get(numero_empleado__iexact=num_emp)
            except Empleado.DoesNotExist:
                messages.error(
                    request,
                    "Acceso denegado: número de empleado no registrado.",
                )
            else:
                if not empleado.activo:
                    messages.error(
                        request,
                        "Acceso denegado: el usuario se encuentra inactivo.",
                    )
                elif empleado.pin == pin_ingresado:
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
                    messages.error(request, "Acceso denegado: PIN incorrecto.")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


def logout_empleado(request):
    """Cierra la sesión de planta y regresa al acceso."""
    request.session.flush()
    return redirect("personal:login")


def matriz_competencias(request):
    empleado_id = request.session.get("empleado_id")
    jefe = Empleado.objects.filter(id=empleado_id).first()
    
    linea_actual = jefe.linea if (jefe and jefe.linea) else Linea.objects.first()
    if not linea_actual:
        return render(request, "matriz.html", {"linea": None, "estaciones": [], "matriz": []})

    # 1. Procesar guardado de asignación (POST)
    if request.method == "POST" and "guardar_asignacion" in request.POST:
        asignaciones_guardadas = {}
        for key, val in request.POST.items():
            if key.startswith("estacion_"):
                estacion_id = key.replace("estacion_", "")
                asignaciones_guardadas[estacion_id] = val if val else None
        
        request.session[f"asignacion_vigente_{linea_actual.id}"] = asignaciones_guardadas
        messages.success(request, "¡Asignación vigente actualizada correctamente!")
        return redirect("personal:matriz_competencias")

    # 2. Consultar datos
    estaciones = Estacion.objects.filter(linea=linea_actual).order_by("orden")
    empleados = Empleado.objects.filter(
        linea=linea_actual, activo=True, rol__tipo_rol__iexact="operador"
    ).order_by("nombre")
    
    habilidades = SkillMatrix.objects.filter(empleado__in=empleados, estacion__in=estaciones)
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
            h.empleado for h in habilidades 
            if h.estacion_id == est.id and h.nivel == "Instructor"
        ]
        instructores_por_estacion[est.id] = instructores

    # 5. CONSTRUIR TABLA 1: ASIGNACIÓN VIGENTE DE LA LÍNEA
    asignacion_session = request.session.get(f"asignacion_vigente_{linea_actual.id}", {})
    tabla_vigente_estatica = []
    
    for est in estaciones:
        emp_id = asignacion_session.get(str(est.id))
        emp_obj = empleados.filter(id=emp_id).first() if emp_id else None
        
        nivel = mapa_habilidades.get((emp_obj.id, est.id)) if emp_obj else None
        # Ahora se activa alerta/instructor para Principiante y Sin Nivel:
        es_principiante = (nivel == "Principiante" or not nivel)
        
        instructores = instructores_por_estacion.get(est.id, [])
        instructor_apoyo = instructores[0] if (es_principiante and instructores) else None
        
        tabla_vigente_estatica.append({
            "estacion": est,
            "empleado_asignado": emp_obj,
            "nivel": nivel,
            "es_principiante": es_principiante,
            "instructor_apoyo": instructor_apoyo
        })

    # 6. CONSTRUIR TABLA 2: SUGERENCIA DE DISTRIBUCIÓN
    sugerencia_propuesta = None
    if request.GET.get("sugerir") == "1":
        sugerencia_propuesta = generar_sugerencia_turno(linea_actual)
        
        for item in sugerencia_propuesta["asignaciones"]:
            emp = item.get("empleado")
            est = item["estacion"]
            
            nivel = mapa_habilidades.get((emp.id, est.id)) if emp else None
            item["nivel"] = nivel
            # Evaluamos si requiere apoyo (Principiante o Sin Nivel)
            item["es_principiante"] = (nivel == "Principiante" or not nivel)
            
            instructores = instructores_por_estacion.get(est.id, [])
            item["instructor_apoyo"] = instructores[0] if (item["es_principiante"] and instructores) else None

    # Mapa de habilidades en formato JSON para reactividad dinámica en JS
    mapa_niveles_json = json.dumps({f"{h.empleado_id}_{h.estacion_id}": h.nivel for h in habilidades})

    return render(
        request,
        "matriz.html",
        {
            "linea": linea_actual,
            "estaciones": estaciones,
            "matriz": matriz,
            "tabla_vigente_estatica": tabla_vigente_estatica,
            "sugerencia_propuesta": sugerencia_propuesta,
            "todos_los_operadores": empleados,
            "mapa_niveles_json": mapa_niveles_json,
        },
    )


@require_POST
def actualizar_nivel_matriz(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Cuerpo JSON inválido"}, status=400
        )

    try:
        nivel = services.actualizar_nivel(
            data.get("empleado_id"), data.get("estacion_id"), data.get("nivel")
        )
    except services.NivelInvalido as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    except Empleado.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Empleado no encontrado"}, status=404
        )
    except Estacion.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Estación no encontrada"}, status=404
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": True, "nivel": nivel})