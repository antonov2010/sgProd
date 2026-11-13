
# Create your models here.
from django.db import models
from django.utils import timezone

class CatalogoDefecto(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.codigo}: {self.descripcion}"

class Asignacion(models.Model):
    # Relacionamos con los modelos creados en la app personal
    empleado = models.ForeignKey('personal.Empleado', on_delete=models.CASCADE)
    estacion = models.ForeignKey('personal.Estacion', on_delete=models.CASCADE)
    # Fecha de planta (TIME_ZONE), no la del reloj del sistema: auto_now_add usa
    # date.today() y en Windows puede quedar en UTC, un día adelante por la tarde.
    fecha = models.DateField(default=timezone.localdate)
    turno = models.IntegerField()
    alerta_supervision = models.BooleanField(default=False)

    def __str__(self):
        return f"Asignación {self.empleado} - Estación {self.estacion} ({self.fecha})"

class RegistroCalidadHorario(models.Model):
    asignacion = models.ForeignKey(Asignacion, on_delete=models.CASCADE, related_name='registros_horarios')
    hora = models.IntegerField(help_text="Hora del turno (1-24)")
    piezas_aceptadas = models.PositiveIntegerField(default=0)
    piezas_rechazadas = models.PositiveIntegerField(default=0)
    piezas_retrabajo = models.PositiveIntegerField(default=0)
    registrado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Hora {self.hora} - {self.asignacion.empleado}"

class DetalleDefecto(models.Model):
    registro = models.ForeignKey(RegistroCalidadHorario, on_delete=models.CASCADE, related_name='defectos')
    defecto = models.ForeignKey(CatalogoDefecto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.defecto.codigo} x{self.cantidad}"