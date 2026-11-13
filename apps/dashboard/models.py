from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# Meta de producción por estación (RF-3.2)
class MetaEstacion(models.Model):
    estacion = models.OneToOneField('personal.Estacion', on_delete=models.CASCADE, related_name='meta')
    piezas_por_hora_meta = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f"Meta {self.estacion}: {self.piezas_por_hora_meta} pzas/hr"


# Registro de Bonos e Incentivos (RF-3.3)
class BonoIncentivo(models.Model):
    empleado = models.ForeignKey('personal.Empleado', on_delete=models.CASCADE)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    monto_bono = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    otorgado = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bono Cero Defectos - {self.empleado.nombre}"


# Alertas de Capacitación Dirigida (RF-3.4)
class AlertaCapacitacion(models.Model):
    estacion = models.ForeignKey('personal.Estacion', on_delete=models.CASCADE)
    empleado = models.ForeignKey('personal.Empleado', on_delete=models.CASCADE, null=True, blank=True)
    motivo = models.TextField()
    resuelto = models.BooleanField(default=False)
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Capacitación requerida: {self.estacion} - {self.empleado}"


# Umbrales de los semáforos del tablero At-a-Glance (US-13).
# Son configuración de negocio: se editan en el panel de administración y el
# tablero cambia de color sin tocar código. Si no hay fila para un indicador,
# se usan los valores por defecto de umbrales.py.
class UmbralSemaforo(models.Model):
    INDICADORES = [
        ("fpy", "FPY (piezas buenas a la primera)"),
        ("meta", "Cumplimiento de meta"),
        ("defectos", "Tasa de defectos"),
    ]

    indicador = models.CharField(max_length=20, choices=INDICADORES, unique=True)
    verde = models.FloatField(help_text="Valor (%) a partir del cual el semáforo está en verde.")
    amarillo = models.FloatField(help_text="Valor (%) que separa el amarillo del rojo.")

    class Meta:
        verbose_name = "Umbral de semáforo"
        verbose_name_plural = "Umbrales de semáforo"
        ordering = ["indicador"]

    def __str__(self):
        return f"{self.get_indicador_display()}: verde {self.verde:g} %, amarillo {self.amarillo:g} %"

    def clean(self):
        from .umbrales import UMBRALES

        super().clean()
        if self.verde is None or self.amarillo is None:
            return
        if not (0 <= self.verde <= 100 and 0 <= self.amarillo <= 100):
            raise ValidationError("Los umbrales deben estar entre 0 y 100.")
        mejor = UMBRALES.get(self.indicador, {}).get("mejor")
        if mejor == "alto" and self.verde < self.amarillo:
            raise ValidationError(
                "En este indicador un valor mayor es mejor: el verde debe ser mayor o igual que el amarillo."
            )
        if mejor == "bajo" and self.verde > self.amarillo:
            raise ValidationError(
                "En este indicador un valor menor es mejor: el verde debe ser menor o igual que el amarillo."
            )


class ConfiguracionBono(models.Model):
    """Regla de negocio configurable para elegibles a bono por cero defectos (US-15)."""

    TIPO_PERIODO = [
        ("dias", "Últimos N días (ventana móvil)"),
        ("rango", "Rango de fechas específico"),
    ]

    tipo_periodo = models.CharField(
        max_length=10,
        choices=TIPO_PERIODO,
        default="dias",
        help_text="Define si se evalúan los últimos N días o un rango fijo de fechas.",
    )
    dias_evaluacion = models.PositiveIntegerField(
        default=7,
        help_text="Cantidad de días hacia atrás a evaluar cuando el tipo es 'Últimos N días'.",
    )
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha inicial (inclusiva) cuando el tipo es 'Rango de fechas específico'.",
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha final (inclusiva) cuando el tipo es 'Rango de fechas específico'.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuración de bono cero defectos"
        verbose_name_plural = "Configuración de bono cero defectos"

    def __str__(self):
        inicio, fin = self.obtener_rango()
        return f"Periodo bono ({self.get_tipo_periodo_display()}): {inicio} al {fin}"

    def clean(self):
        super().clean()
        if self.tipo_periodo == "dias":
            if not self.dias_evaluacion or self.dias_evaluacion < 1:
                raise ValidationError("Los días de evaluación deben ser al menos 1.")
        elif self.tipo_periodo == "rango":
            if not self.fecha_inicio or not self.fecha_fin:
                raise ValidationError("Debes indicar fecha de inicio y fecha de fin para un rango fijo.")
            if self.fecha_inicio > self.fecha_fin:
                raise ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")

    def obtener_rango(self, referencia=None):
        """Devuelve (fecha_inicio, fecha_fin) efectivos a evaluar."""
        hoy = referencia or timezone.localdate()
        if self.tipo_periodo == "rango" and self.fecha_inicio and self.fecha_fin:
            return self.fecha_inicio, self.fecha_fin
        dias = max(self.dias_evaluacion or 7, 1)
        return hoy - timedelta(days=dias - 1), hoy