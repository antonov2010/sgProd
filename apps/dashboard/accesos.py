"""Control de acceso de los tableros (ticket de seguridad).

Cada pantalla del dashboard solo la ve el rol que le corresponde:
gerente -> gerente, jefe -> jefe, operador -> operador.

- Sin sesión de planta: se manda a /personal/login/.
- Con sesión pero de otro rol: 403 (acceso denegado).
Sigue el mismo patrón que jefe_de_linea_requerido (apps/calidad/views.py).
"""

from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.personal.models import Empleado

NOMBRES_ROL = {
    "gerente": "Gerente de Producción",
    "jefe": "Jefe de Línea",
    "operador": "Operador",
}


def rol_requerido(rol):
    """Solo entra un empleado activo, con sesión, que tenga el rol indicado."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            empleado_id = request.session.get("empleado_id")
            if not empleado_id:
                messages.error(request, "Inicia sesión para ver el tablero.")
                return redirect("personal:login")
            empleado = (
                Empleado.objects.filter(pk=empleado_id, activo=True)
                .select_related("rol")
                .first()
            )
            if empleado is None:
                request.session.flush()
                messages.error(request, "Tu sesión ya no es válida. Inicia sesión de nuevo.")
                return redirect("personal:login")
            tipo = empleado.rol.tipo_rol.lower() if empleado.rol else ""
            if tipo != rol:
                raise PermissionDenied(
                    f"Esta pantalla es solo para {NOMBRES_ROL.get(rol, rol)}."
                )
            request.empleado = empleado
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
