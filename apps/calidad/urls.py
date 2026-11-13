from django.urls import path

from . import views

app_name = "calidad"

urlpatterns = [
    path("captura/", views.captura_horaria, name="captura"),
    path("captura/guardar/", views.guardar_captura, name="guardar_captura"),
]
