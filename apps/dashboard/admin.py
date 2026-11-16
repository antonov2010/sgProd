from django.contrib import admin

from .models import ConfiguracionBono, MetaEstacion, UmbralSemaforo


@admin.register(MetaEstacion)
class MetaEstacionAdmin(admin.ModelAdmin):
    """Meta de piezas por hora editable desde el Admin (US-14, RF-3.2)."""

    list_display = ("estacion", "estacion__linea", "piezas_por_hora_meta")
    list_editable = ("piezas_por_hora_meta",)
    list_select_related = ("estacion", "estacion__linea")


@admin.register(UmbralSemaforo)
class UmbralSemaforoAdmin(admin.ModelAdmin):
    """Aquí se cambian los umbrales del tablero sin tocar código (US-13)."""

    list_display = ("indicador", "verde", "amarillo")
    list_editable = ("verde", "amarillo")


@admin.register(ConfiguracionBono)
class ConfiguracionBonoAdmin(admin.ModelAdmin):
    """Regla de negocio configurable para el periodo de bono cero defectos (US-15)."""

    list_display = ("tipo_periodo", "dias_evaluacion", "fecha_inicio", "fecha_fin", "activo")
    list_editable = ("dias_evaluacion", "fecha_inicio", "fecha_fin", "activo")