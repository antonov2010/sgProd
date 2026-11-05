"""Serializers de la API REST de SG-Prod.

Reglas que se respetan aquí:

* Todo es de solo lectura salvo el endpoint de la matriz de habilidades.
* ``Empleado.pin`` **nunca** se serializa: es una credencial de planta.
* Las relaciones se devuelven anidadas en su forma mínima para que el esquema
  de Swagger sea legible y no se vuelva recursivo.
"""

from rest_framework import serializers

from apps.calidad.models import (
    Asignacion,
    CatalogoDefecto,
    DetalleDefecto,
    RegistroCalidadHorario,
)
from apps.dashboard.models import AlertaCapacitacion, BonoIncentivo, MetaEstacion
from apps.personal.models import (
    Empleado,
    Estacion,
    Linea,
    NivelHabilidad,
    Rol,
    SkillMatrix,
)

NIVEL_SIN_ASIGNAR = "Sin nivel"


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ["id", "nombre", "tipo_rol"]


class LineaResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Linea
        fields = ["id", "nombre"]


class EmpleadoResumenSerializer(serializers.ModelSerializer):
    """Vista mínima de un empleado, sin datos de contacto ni PIN."""

    class Meta:
        model = Empleado
        fields = ["id", "numero_empleado", "nombre"]


class EmpleadoSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)
    linea = LineaResumenSerializer(read_only=True)

    class Meta:
        model = Empleado
        fields = ["id", "numero_empleado", "nombre", "rol", "activo", "linea"]
        # ``pin`` queda fuera a propósito: es una credencial, no un dato de consulta.


class EstacionResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estacion
        fields = ["id", "nombre", "orden"]


class EstacionSerializer(serializers.ModelSerializer):
    linea = LineaResumenSerializer(read_only=True)

    class Meta:
        model = Estacion
        fields = ["id", "linea", "nombre", "orden"]


class LineaSerializer(serializers.ModelSerializer):
    jefe_linea = EmpleadoResumenSerializer(read_only=True)
    estaciones = EstacionResumenSerializer(many=True, read_only=True)

    class Meta:
        model = Linea
        fields = ["id", "nombre", "jefe_linea", "estaciones"]


class SkillMatrixSerializer(serializers.ModelSerializer):
    empleado = EmpleadoResumenSerializer(read_only=True)
    estacion = EstacionResumenSerializer(read_only=True)

    class Meta:
        model = SkillMatrix
        fields = ["id", "empleado", "estacion", "nivel"]


class CatalogoDefectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogoDefecto
        fields = ["id", "codigo", "descripcion"]


class AsignacionSerializer(serializers.ModelSerializer):
    empleado = EmpleadoResumenSerializer(read_only=True)
    estacion = EstacionResumenSerializer(read_only=True)

    class Meta:
        model = Asignacion
        fields = [
            "id",
            "empleado",
            "estacion",
            "fecha",
            "turno",
            "alerta_supervision",
        ]


class RegistroCalidadHorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroCalidadHorario
        fields = [
            "id",
            "asignacion",
            "hora",
            "piezas_aceptadas",
            "piezas_rechazadas",
            "piezas_retrabajo",
            "registrado_en",
        ]


class DetalleDefectoSerializer(serializers.ModelSerializer):
    defecto = CatalogoDefectoSerializer(read_only=True)

    class Meta:
        model = DetalleDefecto
        fields = ["id", "registro", "defecto", "cantidad"]


class MetaEstacionSerializer(serializers.ModelSerializer):
    estacion = EstacionResumenSerializer(read_only=True)

    class Meta:
        model = MetaEstacion
        fields = ["id", "estacion", "piezas_por_hora_meta"]


class BonoIncentivoSerializer(serializers.ModelSerializer):
    empleado = EmpleadoResumenSerializer(read_only=True)

    class Meta:
        model = BonoIncentivo
        fields = [
            "id",
            "empleado",
            "periodo_inicio",
            "periodo_fin",
            "monto_bono",
            "otorgado",
            "fecha_registro",
        ]


class AlertaCapacitacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertaCapacitacion
        fields = [
            "id",
            "estacion",
            "empleado",
            "motivo",
            "resuelto",
            "fecha_generacion",
        ]


class ActualizarNivelEntradaSerializer(serializers.Serializer):
    """Cuerpo del POST que crea, cambia o borra un nivel de la matriz."""

    empleado_id = serializers.IntegerField(help_text="ID del empleado (operador).")
    estacion_id = serializers.IntegerField(help_text="ID de la estación.")
    nivel = serializers.ChoiceField(
        choices=[*NivelHabilidad.values, NIVEL_SIN_ASIGNAR],
        help_text=(
            "Nivel a asignar. ``Sin nivel`` elimina la fila de la matriz en "
            "lugar de guardarla."
        ),
    )


class ActualizarNivelRespuestaSerializer(serializers.Serializer):
    """Respuesta del POST de la matriz (éxito o error, mismo contrato)."""

    success = serializers.BooleanField()
    nivel = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Nivel efectivamente guardado (o ``Sin nivel``).",
    )
    error = serializers.CharField(
        required=False, help_text="Mensaje legible cuando ``success`` es false."
    )
