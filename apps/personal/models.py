"""Modelos de personal: empleados, líneas, estaciones y matriz de habilidades."""

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models


class NivelHabilidad(models.TextChoices):
    PRINCIPIANTE = "Principiante", "Principiante"
    AUTONOMO = "Autónomo", "Autónomo"
    EXPERTO = "Experto", "Experto"
    INSTRUCTOR = "Instructor", "Instructor"


class Rol(models.Model):
    nombre = models.CharField(max_length=100)
    tipo_rol = models.CharField(max_length=30, unique=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return f"{self.nombre} ({self.tipo_rol})"


class Linea(models.Model):
    nombre = models.CharField(max_length=50)
    # Jefe de Línea responsable. Es la fuente de verdad para saber qué línea
    # le corresponde a cada jefe; Empleado.linea ubica al resto del personal.
    jefe_linea = models.ForeignKey(
        "Empleado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lineas_a_cargo",
        limit_choices_to={"rol__tipo_rol": "jefe"},
    )

    def __str__(self):
        return self.nombre

    def clean(self):
        """Evita nombrar jefe de línea a alguien que no tiene ese rol."""
        super().clean()
        if not self.jefe_linea_id:
            return
        rol = getattr(self.jefe_linea, "rol", None)
        if rol is None or rol.tipo_rol != "jefe":
            raise ValidationError(
                {"jefe_linea": "El empleado asignado debe tener el rol de Jefe de Línea."}
            )


class Empleado(models.Model):
    """Empleado de planta.

    El PIN de acceso se guarda únicamente como hash: nunca se devuelve ni se
    registra en claro, tampoco en logs ni en el Admin.
    """

    numero_empleado = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    pin_hash = models.CharField(max_length=128, blank=True, null=True)
    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        related_name="empleados",
        null=True,
        blank=True,
    )
    activo = models.BooleanField(default=True)
    # Línea a la que pertenece el empleado (operadores y jefes).
    linea = models.ForeignKey(
        Linea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="empleados",
    )

    def __str__(self):
        return f"{self.numero_empleado} - {self.nombre}"

    def set_pin(self, pin):
        """Guarda el PIN como hash; el valor en claro nunca se conserva."""
        self.pin_hash = make_password(pin)

    def check_pin(self, pin):
        """Valida un PIN contra el hash guardado.

        Es tolerante a empleados sin PIN (``pin_hash`` vacío): en ese caso
        devuelve ``False`` en lugar de fallar. El PIN recibido no se registra.
        """
        if not self.pin_hash:
            return False
        try:
            return check_password(pin, self.pin_hash)
        except ValueError:
            return False


class Estacion(models.Model):
    linea = models.ForeignKey(Linea, on_delete=models.CASCADE, related_name="estaciones")
    nombre = models.CharField(max_length=50)
    orden = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.linea.nombre} - {self.nombre}"


class SkillMatrix(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    estacion = models.ForeignKey(Estacion, on_delete=models.CASCADE)
    nivel = models.CharField(max_length=20, choices=NivelHabilidad.choices)

    class Meta:
        unique_together = ("empleado", "estacion")
