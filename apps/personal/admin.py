"""Admin de personal (US-05, US-06, RF-1.1/RF-1.2).

Empleados, estaciones y la matriz de habilidades se consultan y administran
desde el Admin de Django. El Jefe de Línea solo ve la información de la línea
que tiene asignada.
"""

from django.contrib import admin

from .models import Empleado, Estacion, Linea, Rol, SkillMatrix
from .permisos import lineas_del_usuario


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    """Consulta de empleados: número, nombre, línea y estado."""

    list_display = ("numero_empleado", "nombre", "linea", "activo", "rol")
    list_filter = ("activo", "rol", "linea")
    search_fields = ("numero_empleado", "nombre", "linea__nombre")
    list_select_related = ("linea", "rol")
    # El hash del PIN nunca se edita desde el Admin: solo se muestra de lectura.
    readonly_fields = ("pin_hash",)

    def get_list_filter(self, request):
        """El filtro por línea no se le ofrece a quien solo ve una línea."""
        if request.user.is_superuser:
            return ("activo", "rol", "linea")
        return ("activo", "rol")

    def get_queryset(self, request):
        """Un empleado dado de baja no aparece como disponible.

        Además, el Jefe de Línea solo ve al personal de su propia línea.
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            activo=True,
            linea__in=lineas_del_usuario(request.user),
        )


@admin.register(Estacion)
class EstacionAdmin(admin.ModelAdmin):
    """Consulta de estaciones por línea."""

    list_display = ("nombre", "linea", "orden")
    search_fields = ("nombre",)
    list_select_related = ("linea",)

    def get_list_filter(self, request):
        """El filtro por línea no se le ofrece al Jefe de Línea.

        Mostrarle todas las líneas en el filtro contradice que solo ve su
        propia línea; además solo tiene una, así que el filtro no le aporta.
        """
        if request.user.is_superuser:
            return ("linea",)
        return ()

    def get_queryset(self, request):
        """El Jefe de Línea solo ve las estaciones de su línea."""
        qs = super().get_queryset(request).select_related("linea")
        if request.user.is_superuser:
            return qs
        return qs.filter(linea__in=lineas_del_usuario(request.user))


@admin.register(Linea)
class LineaAdmin(admin.ModelAdmin):
    """Consulta de las líneas de producción y su Jefe de Línea."""

    list_display = ("nombre", "jefe_linea")
    search_fields = ("nombre", "jefe_linea__numero_empleado", "jefe_linea__nombre")
    list_select_related = ("jefe_linea",)

    def get_queryset(self, request):
        """El Jefe de Línea solo ve su propia línea."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(pk__in=lineas_del_usuario(request.user))


@admin.register(SkillMatrix)
class SkillMatrixAdmin(admin.ModelAdmin):
    """Matriz de habilidades, acotada a la línea del Jefe de Línea."""

    list_display = ("empleado", "estacion", "nivel")
    list_filter = ("nivel", "estacion__linea")
    search_fields = (
        "empleado__numero_empleado",
        "empleado__nombre",
        "estacion__nombre",
    )
    list_select_related = ("empleado", "estacion", "estacion__linea")

    def get_list_filter(self, request):
        """No se expone el filtro por línea al Jefe de Línea."""
        if request.user.is_superuser:
            return ("nivel", "estacion__linea")
        return ("nivel",)

    def get_queryset(self, request):
        """El Jefe de Línea solo ve habilidades de empleados y estaciones suyas."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        lineas = lineas_del_usuario(request.user)
        return qs.filter(
            empleado__linea__in=lineas,
            estacion__linea__in=lineas,
        )


admin.site.register(Rol)
