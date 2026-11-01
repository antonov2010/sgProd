    
# Create your models here.
from django.db import models

class NivelHabilidad(models.TextChoices):
    PRINCIPIANTE = 'Principiante', 'Principiante'
    AUTONOMO = 'Autónomo', 'Autónomo'
    EXPERTO = 'Experto', 'Experto'
    INSTRUCTOR = 'Instructor', 'Instructor'


class Rol(models.Model):
    nombre = models.CharField(max_length=100)
    tipo_rol = models.CharField(max_length=30, unique=True)

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return f"{self.nombre} ({self.tipo_rol})"


class Linea(models.Model):
    nombre = models.CharField(max_length=50)
    # Relación del Jefe de Línea apuntando al modelo Empleado
    jefe_linea = models.ForeignKey(
        'Empleado', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='lineas_a_cargo'
    )

    def __str__(self):
        return self.nombre


class Empleado(models.Model):
    numero_empleado = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    pin = models.CharField(max_length=6, blank=True, null=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name='empleados', null=True, blank=True)
    activo = models.BooleanField(default=True)
    linea = models.ForeignKey(
        Linea, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='empleados'
    )

    def __str__(self):
        return f"{self.numero_empleado} - {self.nombre}"


class Estacion(models.Model):
    linea = models.ForeignKey(Linea, on_delete=models.CASCADE, related_name='estaciones')
    nombre = models.CharField(max_length=50)
    orden = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.linea.nombre} - {self.nombre}"


class SkillMatrix(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    estacion = models.ForeignKey(Estacion, on_delete=models.CASCADE)
    nivel = models.CharField(max_length=20, choices=NivelHabilidad.choices)

    class Meta:
        unique_together = ('empleado', 'estacion')