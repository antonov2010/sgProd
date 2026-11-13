"""Admin de calidad: consulta de asignaciones y registros horarios (US-11)."""

from django.contrib import admin

from .models import Asignacion, RegistroCalidadHorario


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ("fecha", "turno", "estacion", "empleado", "alerta_supervision")
    list_filter = ("fecha", "turno", "estacion__linea", "alerta_supervision")
    search_fields = ("empleado__nombre", "empleado__numero_empleado", "estacion__nombre")


@admin.register(RegistroCalidadHorario)
class RegistroCalidadHorarioAdmin(admin.ModelAdmin):
    list_display = (
        "hora",
        "estacion",
        "operador",
        "piezas_aceptadas",
        "piezas_rechazadas",
        "piezas_retrabajo",
        "registrado_en",
    )
    list_filter = ("asignacion__fecha", "asignacion__turno", "asignacion__estacion__linea")
    list_select_related = ("asignacion__estacion", "asignacion__empleado")

    @admin.display(description="Estación", ordering="asignacion__estacion__nombre")
    def estacion(self, obj):
        return obj.asignacion.estacion

    @admin.display(description="Operador", ordering="asignacion__empleado__nombre")
    def operador(self, obj):
        return obj.asignacion.empleado
