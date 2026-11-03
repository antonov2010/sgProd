from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import LoginForm
from .models import Empleado, Estacion, SkillMatrix, Linea  # <--- Agregamos estos 3


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
                    request.session["numero_empleado"] = empleado.numero_empleado  # <- AGREGA ESTA LÍNEA
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
    """Cierra la sesión de planta y regresa al acceso.

    Es solo el cableado mínimo del enlace que ya existía en las pantallas;
    los permisos por rol se trabajan en una historia posterior.
    """
    request.session.flush()
    return redirect("personal:login")

def matriz_competencias(request):
    # 1. Obtener la sesión del jefe
    empleado_id = request.session.get("empleado_id")
    jefe = Empleado.objects.filter(id=empleado_id).first()
    
    # 2. Determinar la línea del jefe
    linea_actual = jefe.linea if (jefe and jefe.linea) else Linea.objects.first()

    if not linea_actual:
        return render(request, "matriz.html", {
            "linea": None,
            "estaciones": [],
            "matriz": []
        })

    # 3. CRITERIO 1 CORREGIDO:
    # -> Estaciones SOLO de la línea actual
    estaciones = Estacion.objects.filter(linea=linea_actual).order_by("orden")
    
    # -> Empleados ACTIVOS y OPERADORES SOLO de la línea actual
    empleados = Empleado.objects.filter(
        linea=linea_actual, 
        activo=True,
        rol__tipo_rol__iexact="operador"
    ).order_by("nombre")

    # 4. Traer los registros de la matriz de habilidades
    habilidades = SkillMatrix.objects.filter(empleado__in=empleados, estacion__in=estaciones)
    mapa_habilidades = {(h.empleado_id, h.estacion_id): h.nivel for h in habilidades}

    # 5. Construir la matriz
    matriz = []
    for emp in empleados:
        fila_niveles = []
        for est in estaciones:
            nivel = mapa_habilidades.get((emp.id, est.id), None)
            fila_niveles.append({
                "estacion_id": est.id,
                "nivel": nivel
            })
        
        matriz.append({
            "empleado": emp,
            "niveles": fila_niveles
        })

    return render(request, "matriz.html", {
        "linea": linea_actual,
        "estaciones": estaciones,
        "matriz": matriz,
    })

