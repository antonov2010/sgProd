from django.contrib import admin

from .models import ConfiguracionBono, UmbralSemaforo


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