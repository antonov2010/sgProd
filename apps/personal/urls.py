from django.urls import path

from . import views

app_name = "personal"

urlpatterns = [
    path("login/", views.login_empleado, name="login"),
    path("logout/", views.logout_empleado, name="logout"),
    path("matriz/", views.matriz_competencias, name="matriz_competencias"),
    path(
        "matriz/actualizar-nivel/",
        views.actualizar_nivel_matriz,
        name="actualizar_nivel_matriz",
    ),
]
