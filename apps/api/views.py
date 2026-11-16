"""Vistas de la API REST de SG-Prod.

Todas las colecciones son de **solo lectura**. La única escritura es el POST de
la matriz de habilidades, que reutiliza ``apps.personal.services`` para no
duplicar las reglas de negocio de la pantalla HTML.
"""

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.calidad.models import (
    Asignacion,
    CatalogoDefecto,
    DetalleDefecto,
    RegistroCalidadHorario,
)
from apps.dashboard.models import AlertaCapacitacion, BonoIncentivo, MetaEstacion
from apps.personal import services
from apps.personal.models import Empleado, Estacion, Linea, Rol, SkillMatrix
from apps.personal.permisos import LineaNoPermitida, linea_autorizada

from .serializers import (
    ActualizarNivelEntradaSerializer,
    ActualizarNivelRespuestaSerializer,
    AlertaCapacitacionSerializer,
    AsignacionSerializer,
    BonoIncentivoSerializer,
    CatalogoDefectoSerializer,
    DetalleDefectoSerializer,
    EmpleadoSerializer,
    EstacionSerializer,
    LineaSerializer,
    MetaEstacionSerializer,
    RegistroCalidadHorarioSerializer,
    RolSerializer,
    SkillMatrixSerializer,
)


def _aplanar_errores(errores):
    """Convierte los errores de un serializer en un solo mensaje legible."""
    partes = []
    for campo, mensajes in errores.items():
        if not isinstance(mensajes, (list, tuple)):
            mensajes = [mensajes]
        partes.append(f"{campo}: {' '.join(str(m) for m in mensajes)}")
    return "; ".join(partes)


class TagPorDominioSchema(AutoSchema):
    """Agrupa las operaciones en Swagger por dominio (`personal`, `calidad`…)."""

    def get_tags(self):
        dominio = getattr(self.view, "dominio", None)
        return [dominio] if dominio else super().get_tags()


class ColeccionSoloLectura(viewsets.ReadOnlyModelViewSet):
    """Consulta de solo lectura: lista paginada (``GET``) y detalle por ``id``."""

    schema = TagPorDominioSchema()
    dominio = None


class RolViewSet(ColeccionSoloLectura):
    queryset = Rol.objects.all().order_by("nombre")
    serializer_class = RolSerializer
    dominio = "personal"
    search_fields = ["nombre", "tipo_rol"]
    ordering_fields = ["nombre", "tipo_rol"]


class LineaViewSet(ColeccionSoloLectura):
    queryset = (
        Linea.objects.select_related("jefe_linea")
        .prefetch_related("estaciones")
        .order_by("nombre")
    )
    serializer_class = LineaSerializer
    dominio = "personal"
    search_fields = ["nombre"]
    ordering_fields = ["nombre"]


class EmpleadoViewSet(ColeccionSoloLectura):
    queryset = Empleado.objects.select_related("rol", "linea").order_by("nombre")
    serializer_class = EmpleadoSerializer
    dominio = "personal"
    search_fields = ["numero_empleado", "nombre"]
    ordering_fields = ["numero_empleado", "nombre", "activo"]


class EstacionViewSet(ColeccionSoloLectura):
    queryset = Estacion.objects.select_related("linea").order_by("linea__nombre", "orden")
    serializer_class = EstacionSerializer
    dominio = "personal"
    search_fields = ["nombre", "linea__nombre"]
    ordering_fields = ["nombre", "orden"]


class SkillMatrixViewSet(ColeccionSoloLectura):
    queryset = SkillMatrix.objects.select_related(
        "empleado", "estacion", "estacion__linea"
    ).order_by("empleado__nombre", "estacion__orden")
    serializer_class = SkillMatrixSerializer
    dominio = "matriz"
    search_fields = ["empleado__nombre", "empleado__numero_empleado", "estacion__nombre"]
    ordering_fields = ["nivel", "empleado__nombre"]


class CatalogoDefectoViewSet(ColeccionSoloLectura):
    queryset = CatalogoDefecto.objects.all().order_by("codigo")
    serializer_class = CatalogoDefectoSerializer
    dominio = "calidad"
    search_fields = ["codigo", "descripcion"]
    ordering_fields = ["codigo", "descripcion"]


class AsignacionViewSet(ColeccionSoloLectura):
    queryset = Asignacion.objects.select_related("empleado", "estacion").order_by("-fecha")
    serializer_class = AsignacionSerializer
    dominio = "calidad"
    search_fields = ["empleado__nombre", "estacion__nombre"]
    ordering_fields = ["fecha", "turno"]


class RegistroCalidadHorarioViewSet(ColeccionSoloLectura):
    queryset = RegistroCalidadHorario.objects.select_related("asignacion").order_by(
        "asignacion__fecha", "hora"
    )
    serializer_class = RegistroCalidadHorarioSerializer
    dominio = "calidad"
    search_fields = ["asignacion__empleado__nombre"]
    ordering_fields = ["hora", "piezas_aceptadas", "piezas_rechazadas"]


class DetalleDefectoViewSet(ColeccionSoloLectura):
    queryset = DetalleDefecto.objects.select_related("defecto", "registro").order_by("id")
    serializer_class = DetalleDefectoSerializer
    dominio = "calidad"
    search_fields = ["defecto__codigo", "defecto__descripcion"]
    ordering_fields = ["cantidad"]


class MetaEstacionViewSet(ColeccionSoloLectura):
    queryset = MetaEstacion.objects.select_related("estacion").order_by("estacion__nombre")
    serializer_class = MetaEstacionSerializer
    dominio = "dashboard"
    search_fields = ["estacion__nombre"]
    ordering_fields = ["piezas_por_hora_meta"]


class BonoIncentivoViewSet(ColeccionSoloLectura):
    queryset = BonoIncentivo.objects.select_related("empleado").order_by(
        "-periodo_inicio"
    )
    serializer_class = BonoIncentivoSerializer
    dominio = "dashboard"
    search_fields = ["empleado__nombre", "empleado__numero_empleado"]
    ordering_fields = ["periodo_inicio", "monto_bono"]


class AlertaCapacitacionViewSet(ColeccionSoloLectura):
    queryset = AlertaCapacitacion.objects.select_related(
        "estacion", "empleado"
    ).order_by("-fecha_generacion")
    serializer_class = AlertaCapacitacionSerializer
    dominio = "dashboard"
    search_fields = ["motivo", "estacion__nombre", "empleado__nombre"]
    ordering_fields = ["fecha_generacion", "resuelto"]


class MatrizNivelView(APIView):
    """Crea, actualiza o elimina un nivel de la matriz de habilidades.

    Es el equivalente REST de la pantalla ``/personal/matriz/``; ambas rutas
    comparten ``apps.personal.services.actualizar_nivel``.
    """

    @extend_schema(
        tags=["matriz"],
        summary="Asignar o quitar el nivel de un empleado en una estación",
        description=(
            "Envía un nivel del catálogo para crearlo o actualizarlo. "
            "``Sin nivel`` elimina la fila de la matriz.\n\n"
            "**Requiere autenticación.** Con sesión de Django, DRF exige el "
            "token CSRF (Swagger UI lo envía solo). El Jefe de Línea solo "
            "puede editar empleados y estaciones de su propia línea."
        ),
        request=ActualizarNivelEntradaSerializer,
        responses={
            200: ActualizarNivelRespuestaSerializer,
            400: ActualizarNivelRespuestaSerializer,
            403: ActualizarNivelRespuestaSerializer,
            404: ActualizarNivelRespuestaSerializer,
        },
    )
    def post(self, request):
        entrada = ActualizarNivelEntradaSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"success": False, "error": _aplanar_errores(entrada.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        datos = entrada.validated_data

        empleado = Empleado.objects.filter(pk=datos["empleado_id"]).first()
        if empleado is None:
            return Response(
                {"success": False, "error": "Empleado no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        estacion = Estacion.objects.filter(pk=datos["estacion_id"]).first()
        if estacion is None:
            return Response(
                {"success": False, "error": "Estación no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            linea = linea_autorizada(request.user, empleado, estacion)
        except LineaNoPermitida as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            nivel = services.actualizar_nivel(
                empleado.pk, estacion.pk, datos["nivel"], linea=linea
            )
        except services.NivelInvalido as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Empleado.DoesNotExist:
            return Response(
                {"success": False, "error": "Empleado no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Estacion.DoesNotExist:
            return Response(
                {"success": False, "error": "Estación no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"success": True, "nivel": nivel})
