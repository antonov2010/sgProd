from django.contrib import admin

from .models import UmbralSemaforo


@admin.register(UmbralSemaforo)
class UmbralSemaforoAdmin(admin.ModelAdmin):
    """Aquí se cambian los umbrales del tablero sin tocar código (US-13)."""

    list_display = ("indicador", "verde", "amarillo")
    list_editable = ("verde", "amarillo")
