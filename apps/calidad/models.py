from django.db import models
from django.utils import timezone


class CatalogoDefecto(models.Model):
    """Catálogo maestro de códigos de defecto de manufactura."""
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.CharField(max_length=150)

    class Meta:
        verbose_name = "Catálogo de Defecto"
        verbose_name_plural = "Catálogo de Defectos"
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo}: {self.descripcion}"


class Asignacion(models.Model):
    """
    Asignación operativa de un empleado a una estación específica
    para una fecha de planta y turno determinados.
    """
    empleado = models.ForeignKey(
        'personal.Empleado',
        on_delete=models.CASCADE,
        related_name='asignaciones',
    )
    estacion = models.ForeignKey(
        'personal.Estacion',
        on_delete=models.CASCADE,
        related_name='asignaciones',
    )
    # Fecha de planta (TIME_ZONE), no la del reloj del sistema: auto_now_add usa
    # date.today() y en Windows puede quedar en UTC, un día adelante por la tarde.
    fecha = models.DateField(default=timezone.localdate)
    turno = models.IntegerField()
    alerta_supervision = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Asignación"
        verbose_name_plural = "Asignaciones"
        ordering = ['-fecha', 'turno', 'estacion']
        constraints = [
            models.UniqueConstraint(
                fields=['estacion', 'fecha', 'turno'],
                name='uq_calidad_asignacion_estacion_fecha_turno',
            )
        ]
        indexes = [
            models.Index(
                fields=['fecha', 'turno'],
                name='idx_calidad_asig_fecha_turno',
            ),
        ]

    def __str__(self):
        return (
            f"Asignación {self.empleado} - Estación {self.estacion} "
            f"({self.fecha} | Turno {self.turno})"
        )


class RegistroCalidadHorario(models.Model):
    """Captura horaria de piezas producidas y defectuosas por asignación."""
    asignacion = models.ForeignKey(
        Asignacion,
        on_delete=models.CASCADE,
        related_name='registros_horarios',
    )
    hora = models.IntegerField(help_text="Hora del turno (1-24)")
    piezas_aceptadas = models.PositiveIntegerField(default=0)
    piezas_rechazadas = models.PositiveIntegerField(default=0)
    piezas_retrabajo = models.PositiveIntegerField(default=0)
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Calidad Horario"
        verbose_name_plural = "Registros de Calidad Horarios"
        ordering = ['asignacion', 'hora']

    def __str__(self):
        return f"Hora {self.hora} - {self.asignacion.empleado}"


class DetalleDefecto(models.Model):
    """Desglose de defectos detectados dentro de un registro horario."""
    registro = models.ForeignKey(
        RegistroCalidadHorario,
        on_delete=models.CASCADE,
        related_name='defectos',
    )
    defecto = models.ForeignKey(CatalogoDefecto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Detalle de Defecto"
        verbose_name_plural = "Detalles de Defectos"

    def __str__(self):
        return f"{self.defecto.codigo} x{self.cantidad}"