"""Rutas de la API REST y de la documentación Swagger.

    /api/docs/     Swagger UI (interfaz interactiva)
    /api/redoc/    ReDoc (misma especificación, lectura)
    /api/schema/   Esquema OpenAPI 3 en YAML (lo consume la UI)
    /api/          Redirige a la documentación
"""

from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import SimpleRouter

from . import views

app_name = "api"

router = SimpleRouter()
router.register("roles", views.RolViewSet, basename="rol")
router.register("lineas", views.LineaViewSet, basename="linea")
router.register("empleados", views.EmpleadoViewSet, basename="empleado")
router.register("estaciones", views.EstacionViewSet, basename="estacion")
router.register("skill-matrix", views.SkillMatrixViewSet, basename="skillmatrix")
router.register("defectos", views.CatalogoDefectoViewSet, basename="defecto")
router.register("asignaciones", views.AsignacionViewSet, basename="asignacion")
router.register(
    "registros-calidad", views.RegistroCalidadHorarioViewSet, basename="registrocalidad"
)
router.register(
    "detalles-defecto", views.DetalleDefectoViewSet, basename="detalledefecto"
)
router.register("metas-estacion", views.MetaEstacionViewSet, basename="metaestacion")
router.register("bonos", views.BonoIncentivoViewSet, basename="bono")
router.register(
    "alertas-capacitacion", views.AlertaCapacitacionViewSet, basename="alertacapacitacion"
)

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="api:swagger-ui", permanent=False)),
    path("", include(router.urls)),
    path("matriz/nivel/", views.MatrizNivelView.as_view(), name="matriz-nivel"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="api:schema"),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(url_name="api:schema"),
        name="redoc",
    ),
]
